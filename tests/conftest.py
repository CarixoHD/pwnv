import importlib
import json
import sys
from typing import Iterable

import pytest


def _reload_modules(module_names: Iterable[str]) -> None:
    """Reload pwnv modules so they pick up fresh environment variables."""
    importlib.invalidate_caches()
    for name in module_names:
        if name in sys.modules:
            importlib.reload(sys.modules[name])
        else:
            importlib.import_module(name)


# Modules that cache the config path at import time, in dependency order.
# `pwnv.core` comes last on purpose: it re-exports the plugin_manager singleton,
# so reloading the submodule alone leaves every `from pwnv.core import
# plugin_manager` caller holding the previous test's instance.
_RELOADED_MODULES = (
    "pwnv.utils.config",
    "pwnv.utils.plugin",
    "pwnv.utils.remote",
    "pwnv.utils.crud",
    "pwnv.utils.guards",
    "pwnv.core.plugin_manager",
    "pwnv.core.setup",
    "pwnv.core",
)


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch, tmp_path):
    """
    Force pwnv to use an isolated config file under a temporary directory.

    This prevents tests from touching the user's real config or CTF folders.
    """
    cfg_dir = tmp_path / "pwnv_config_dir"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = cfg_dir / "pwnv_config.json"
    ctfs_path = cfg_dir / "ctfs"
    ctfs_path.mkdir(parents=True, exist_ok=True)

    cfg_path.write_text(
        json.dumps(
            {
                "ctfs_path": str(ctfs_path),
                "challenge_tags": [],
                "ctfs": [],
                "challenges": [],
            }
        ),
        encoding="utf-8",
    )

    # Make pwnv resolve all config paths inside our temp directory.
    monkeypatch.setenv("PWNV_CONFIG", str(cfg_path))
    # Ensure debug override is off.
    monkeypatch.delenv("PWNV_DEBUG", raising=False)

    # Reload modules that cache the config path at import time.
    _reload_modules(_RELOADED_MODULES)

    yield cfg_path

    # Clear cached config between tests.
    cfg_mod = sys.modules.get("pwnv.utils.config")
    if cfg_mod and hasattr(cfg_mod, "load_config"):
        cfg_mod.load_config.cache_clear()


@pytest.fixture
def reload_pwnv_modules():
    """
    Helper fixture to force-reload pwnv modules on demand.

    Useful in tests that change environment variables mid-test.
    """

    def _reload():
        _reload_modules(_RELOADED_MODULES)

    return _reload
