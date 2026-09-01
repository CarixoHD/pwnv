"""Utilities for loading and storing the ``pwnv`` configuration.

The configuration is stored as JSON on disk.  This module resolves the
location of that file, exposes helpers to read and write it and provides
simple accessor helpers used across the code base.
"""

import os
from collections.abc import Generator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from filelock import SoftFileLock

load_dotenv()

_EMPTY_CONFIG: dict = {"ctfs": [], "challenges": [], "challenge_tags": []}


def _resolve_config_path() -> Path:
    """Return the path of the configuration file."""
    from pwnv.constants import DEFAULT_CONFIG_BASENAME, PWNV_CONFIG_ENV

    if override := os.getenv(PWNV_CONFIG_ENV):
        return Path(override).expanduser().resolve()

    for parent in (Path.cwd(), *Path.cwd().parents):
        candidate = parent / DEFAULT_CONFIG_BASENAME
        if candidate.is_file():
            return candidate

    # click rather than typer, which re-exports this same function: this is the
    # branch a default install takes, and `from pwnv import challenge` reaches
    # it, so a solve script would import the whole CLI to find its config.
    from click import get_app_dir

    return Path(get_app_dir("pwnv")) / DEFAULT_CONFIG_BASENAME


config_path: Path = _resolve_config_path()
config_path.parent.mkdir(parents=True, exist_ok=True)
_lock = SoftFileLock(str(config_path) + ".lock")


def _read_config_file() -> dict:
    """Read the configuration straight from disk, bypassing the cache."""
    import json

    if not config_path.exists():
        return dict(_EMPTY_CONFIG)
    try:
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        import typer

        from pwnv.utils.ui import error, info

        error(f"Configuration at {config_path} is not valid JSON: {exc}.")
        info(
            "Restore it from a backup, or repair the file by hand - "
            "pwnv will not overwrite it while it cannot be parsed."
        )
        raise typer.Exit(code=1) from exc


@lru_cache(maxsize=1)
def load_config() -> dict:
    """Load and return the JSON configuration as a dictionary."""
    return _read_config_file()


def _invalidate_cache() -> None:
    """Clear the cached configuration."""
    load_config.cache_clear()


def _write_config_file(cfg: dict) -> None:
    """Serialise ``cfg`` to disk via a temp file and an atomic rename."""
    import json
    import os
    from tempfile import NamedTemporaryFile

    for key, empty in _EMPTY_CONFIG.items():
        cfg.setdefault(key, list(empty))

    cfg_json = json.dumps(cfg, indent=4, default=str)
    with NamedTemporaryFile(
        "w", dir=config_path.parent, delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(cfg_json)
        tmp.flush()
        os.fsync(tmp.fileno())
    Path(tmp.name).replace(config_path)


def save_config(cfg: dict) -> None:
    """Write ``cfg`` to disk atomically and invalidate the cache."""
    with _lock:
        _write_config_file(cfg)
    _invalidate_cache()


@contextmanager
def config_transaction() -> Generator[dict]:
    """
    Yield the configuration for mutation, holding the lock for the whole cycle.

    Reading and writing under a single lock keeps concurrent ``pwnv`` processes
    from clobbering each other: without it two commands can both read the same
    config, each apply their own change, and the second write silently discards
    the first (a lost solve or a lost synced challenge).
    """
    with _lock:
        cfg = _read_config_file()
        yield cfg
        _write_config_file(cfg)
    _invalidate_cache()


def get_config_path() -> Path:
    """Return the resolved configuration path."""
    return config_path


def get_ctfs_path() -> Path:
    """Return the path on disk where CTFs are stored."""
    config = load_config()
    return Path(config["ctfs_path"])


def get_config_value(key: str) -> Any:
    """Return a value from the configuration by ``key``."""
    config = load_config()
    return config.get(key)


def set_config_value(key: str, value: Any) -> None:
    """Set a ``key`` in the configuration and persist it."""
    config = load_config()
    config[key] = value
    save_config(config)
