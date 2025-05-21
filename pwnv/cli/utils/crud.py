import shutil
from pathlib import Path
from typing import List

from pwnv.cli.utils.config import load_config, save_config
from pwnv.models import CTF, Challenge
from pwnv.models.challenge import Solved


# -- [CRUD] --
# [READ]
def get_ctfs() -> List[CTF]:
    return [CTF(**ctf) for ctf in load_config().get("ctfs", [])]


def get_challenges() -> List[Challenge]:
    return [Challenge(**ch) for ch in load_config().get("challenges", [])]


def get_running_ctfs() -> List[CTF]:
    return [ctf for ctf in get_ctfs() if ctf.running]


def get_stopped_ctfs() -> List[CTF]:
    return [ctf for ctf in get_ctfs() if not ctf.running]


def get_unsolved_challenges() -> List[Challenge]:
    return [ch for ch in get_challenges() if ch.solved == Solved.unsolved]


def get_solved_challenges() -> List[Challenge]:
    return [ch for ch in get_challenges() if ch.solved == Solved.solved]


def challenges_for_ctf(ctf: CTF) -> List[Challenge]:
    return [ch for ch in get_challenges() if ch.ctf_id == ctf.id]


def ctfs_with_challenges() -> List[CTF]:
    populated = {ch.ctf_id for ch in get_challenges()}
    return [ctf for ctf in get_ctfs() if ctf.id in populated]


def get_ctf_by_challenge(ch: Challenge) -> CTF | None:
    for ctf in get_ctfs():
        if ch.ctf_id == ctf.id:
            return ctf
    return None


def get_tags() -> set[str]:
    return set(load_config().get("challenge_tags", []))


def get_current_ctf(path: Path = Path.cwd()) -> CTF | None:
    for ctf in get_ctfs():
        if path.is_relative_to(ctf.path):
            return ctf
    return None


def get_current_challenge(path: Path = Path.cwd()) -> Challenge | None:
    for ch in get_challenges():
        if path.is_relative_to(ch.path):
            return ch
    return None


# [CREATE]
def add_ctf(ctf: CTF) -> None:
    cfg = load_config()
    cfg.setdefault("ctfs", []).append(ctf.model_dump())
    save_config(cfg)
    ctf.path.mkdir(parents=True, exist_ok=True)


def add_challenge(ch: Challenge) -> None:
    from pwnv.setup import Core

    cfg = load_config()
    cfg.setdefault("challenges", []).append(ch.model_dump())
    save_config(cfg)
    ch.path.mkdir(parents=True, exist_ok=True)
    Core(ch)


def add_tags(tags: set[str]) -> None:
    cfg = load_config()
    cfg["challenge_tags"] = list(
        set(cfg.get("challenge_tags", [])) | {t.lower() for t in tags}
    )
    save_config(cfg)


# [UPDATE]
def update_ctf(ctf: CTF) -> None:
    cfg = load_config()
    ctfs = cfg.setdefault("ctfs", [])
    for idx, c in enumerate(ctfs):
        if c["id"] == str(ctf.id):
            ctfs[idx] = ctf.model_dump()
            break
    save_config(cfg)


def update_challenge(ch: Challenge) -> None:
    cfg = load_config()
    challenges = cfg.setdefault("challenges", [])
    for idx, item in enumerate(challenges):
        if item["id"] == str(ch.id):
            challenges[idx] = ch.model_dump()
            break
    save_config(cfg)


# [DELETE]
def remove_ctf(ctf: CTF) -> None:
    cfg = load_config()
    cfg["ctfs"] = [c for c in cfg.get("ctfs", []) if c["id"] != str(ctf.id)]
    cfg["challenges"] = [
        ch for ch in cfg.get("challenges", []) if ch["ctf_id"] != str(ctf.id)
    ]
    save_config(cfg)
    if ctf.path.exists():
        shutil.rmtree(ctf.path)


def remove_challenge(ch: Challenge) -> None:
    cfg = load_config()
    cfg["challenges"] = [
        item for item in cfg.get("challenges", []) if item["id"] != str(ch.id)
    ]
    save_config(cfg)
    if ch.path.exists():
        shutil.rmtree(ch.path)


# [MISC]
def is_duplicate(
    *,
    name: str | None = None,
    path: Path | None = None,
    model_list: List[CTF | Challenge],
) -> bool:
    if path is None:
        return any(model.name == name for model in model_list)
    elif name is None:
        return any(model.path == path for model in model_list)
    return any(model.name == name or model.path == path for model in model_list)
