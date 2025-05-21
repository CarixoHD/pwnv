import json
import os
from functools import lru_cache
from pathlib import Path
from tempfile import NamedTemporaryFile

from dotenv import load_dotenv
from filelock import SoftFileLock

load_dotenv()

_CONFIG_ENV: str = "PWNV_CONFIG"
_DEBUG_ENV: str = "PWNV_DEBUG"
_DEFAULT_BASENAME = "config.json"


def _resolve_config_path() -> Path:
    import typer

    if override := os.getenv(_CONFIG_ENV):
        return Path(override).expanduser().resolve()

    if os.getenv(_DEBUG_ENV):
        return Path("/tmp/pwnv") / _DEFAULT_BASENAME

    for parent in (Path.cwd(), *Path.cwd().parents):
        candidate = parent / _DEFAULT_BASENAME
        if candidate.is_file():
            return candidate

    return Path(typer.get_app_dir("pwnv")) / _DEFAULT_BASENAME


config_path: Path = _resolve_config_path()
config_path.parent.mkdir(parents=True, exist_ok=True)
_lock = SoftFileLock(str(config_path) + ".lock")


@lru_cache(maxsize=1)
def load_config() -> dict:
    if not config_path.exists():
        return {"ctfs": [], "challenges": [], "challenge_tags": []}
    with open(config_path) as f:
        return json.load(f)


def _invalidate_cache() -> None:
    load_config.cache_clear()


def save_config(cfg: dict) -> None:
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
    return config_path


def get_ctfs_path() -> Path:
    config = load_config()
    return Path(config["ctfs_path"])
