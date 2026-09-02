import importlib
import json
import sys
from typing import Iterable

import pytest


def _reload_modules(module_names: Iterable[str]) -> None:
    importlib.invalidate_caches()
    for name in module_names:
        if name in sys.modules:
            importlib.reload(sys.modules[name])
        else:
            importlib.import_module(name)


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

    monkeypatch.setenv("PWNV_CONFIG", str(cfg_path))
    _reload_modules(_RELOADED_MODULES)

    yield cfg_path

    cfg_mod = sys.modules.get("pwnv.utils.config")
    if cfg_mod and hasattr(cfg_mod, "load_config"):
        cfg_mod.load_config.cache_clear()


@pytest.fixture
def reload_pwnv_modules():
    def _reload():
        _reload_modules(_RELOADED_MODULES)

    return _reload
