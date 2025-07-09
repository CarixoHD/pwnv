"""Utilities for loading and storing the ``pwnv`` configuration.

The configuration is stored as JSON on disk.  This module resolves the
location of that file, exposes helpers to read and write it and provides
simple accessor helpers used across the code base.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from filelock import SoftFileLock

load_dotenv()


def _resolve_config_path() -> Path:
    """Return the path of the configuration file."""
    import os

    import typer

    from pwnv.constants import DEFAULT_CONFIG_BASENAME, PWNV_CONFIG_ENV, PWNV_DEBUG_ENV

    if override := os.getenv(PWNV_CONFIG_ENV):
        return Path(override).expanduser().resolve()

    if os.getenv(PWNV_DEBUG_ENV):
        return Path("/tmp/pwnv") / DEFAULT_CONFIG_BASENAME

    for parent in (Path.cwd(), *Path.cwd().parents):
        candidate = parent / DEFAULT_CONFIG_BASENAME
        if candidate.is_file():
            return candidate

    return Path(typer.get_app_dir("pwnv")) / DEFAULT_CONFIG_BASENAME


config_path: Path = _resolve_config_path()
config_path.parent.mkdir(parents=True, exist_ok=True)
_lock = SoftFileLock(str(config_path) + ".lock")


@lru_cache(maxsize=1)
def load_config() -> dict:
    """Load and return the JSON configuration as a dictionary."""
    import json

    if not config_path.exists():
        return {"ctfs": [], "challenges": [], "challenge_tags": []}
    with open(config_path) as f:
        return json.load(f)


def _invalidate_cache() -> None:
    """Clear the cached configuration."""
    load_config.cache_clear()


def save_config(cfg: dict) -> None:
    """Write ``cfg`` to disk atomically and invalidate the cache."""
    import json
    import os
    from tempfile import NamedTemporaryFile

    cfg.setdefault("ctfs", [])
    cfg.setdefault("challenges", [])
    cfg.setdefault("challenge_tags", [])

    with _lock:
        cfg_json = json.dumps(cfg, indent=4, default=str)
        with NamedTemporaryFile(
            "w", dir=config_path.parent, delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(cfg_json)
            tmp.flush()
            os.fsync(tmp.fileno())
        Path(tmp.name).replace(config_path)
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
