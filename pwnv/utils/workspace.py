"""Backup and portability helpers for pwnv workspaces."""

import json
import tarfile
from pathlib import Path

from pwnv.constants import DEFAULT_PWNVENV_FOLDER_NAME
from pwnv.models import Init

_VENV_DIR_NAMES = (DEFAULT_PWNVENV_FOLDER_NAME, ".venv")


def _is_virtualenv_artifact(path: Path) -> bool:
    """Return ``True`` if ``path`` lives inside a generated virtualenv."""
    return any(name in path.parts for name in _VENV_DIR_NAMES)


def backup_workspace(destination: Path) -> Path:
    """Create a complete ``tar.gz`` backup and return its final path."""
    from pwnv.utils.config import get_config_path, get_ctfs_path

    destination = destination.expanduser().resolve()
    if not str(destination).endswith(".tar.gz"):
        destination = destination.with_name(destination.name + ".tar.gz")
    destination.parent.mkdir(parents=True, exist_ok=True)

    config_path = get_config_path()
    ctfs_path = get_ctfs_path()
    with tarfile.open(destination, "w:gz") as archive:
        archive.add(config_path, arcname=f"config/{config_path.name}")
        for path in ctfs_path.rglob("*"):
            if path.resolve() == destination:
                continue
            if _is_virtualenv_artifact(path):
                continue
            archive.add(
                path,
                arcname=Path("ctfs") / path.relative_to(ctfs_path),
                recursive=False,
            )
    return destination


def restore_workspace(
    source: Path, *, replace: bool = False, force: bool = False
) -> dict[str, int]:
    """
    Restore a ``workspace backup`` archive into the current workspace.
    """
    import tempfile

    from pwnv.utils.config import get_ctfs_path

    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"No backup archive at {source}.")

    destination_root = get_ctfs_path().resolve()
    with tempfile.TemporaryDirectory() as workdir:
        staged = Path(workdir)
        with tarfile.open(source, "r:gz") as archive:
            archive.extractall(staged, filter="data")

        config_file = next(iter(sorted((staged / "config").glob("*.json"))), None)
        if config_file is None:
            raise ValueError(
                f"{source} does not look like a pwnv backup - it has no config "
                "in it. `workspace import` reads the JSON exports instead."
            )

        data = json.loads(config_file.read_text(encoding="utf-8"))
        imported = Init.model_validate(data)
        source_root = Path(str(data.get("ctfs_path") or ""))
        restored = _copy_tree(staged / "ctfs", destination_root, force=force)

    _rebase_by_layout(imported, source_root, destination_root)
    imported.ctfs_path = destination_root
    summary = _merge_records(imported, replace=replace)
    summary["files_restored"] = restored
    return summary


def _copy_tree(source_root: Path, destination_root: Path, *, force: bool) -> int:
    """Copy the archived tree into place and report how many files landed."""
    import shutil

    if not source_root.is_dir():
        return 0

    restored = 0
    destination_root.mkdir(parents=True, exist_ok=True)
    for path in sorted(source_root.rglob("*")):
        target = destination_root / path.relative_to(source_root)
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if target.exists() and not force:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        restored += 1
    return restored


def _rebase_by_layout(
    imported: Init, source_root: Path, destination_root: Path
) -> None:
    """
    Move every record to the same place under the new CTF root.
    """
    from pwnv.utils.remote import sanitize

    ctf_paths: dict = {}
    for ctf in imported.ctfs:
        if ctf is None:
            continue
        ctf.path = _relocate(ctf.path, source_root, destination_root) or (
            destination_root / sanitize(ctf.name)
        )
        ctf.path.mkdir(parents=True, exist_ok=True)
        ctf_paths[ctf.id] = ctf.path

    for challenge in imported.challenges:
        if challenge is None or challenge.ctf_id not in ctf_paths:
            continue
        challenge.path = _relocate(challenge.path, source_root, destination_root) or (
            ctf_paths[challenge.ctf_id]
            / challenge.category.name
            / sanitize(challenge.name)
        )
        challenge.path.mkdir(parents=True, exist_ok=True)


def _relocate(path: Path, source_root: Path, destination_root: Path) -> Path | None:
    """The same relative location under a different root, if there is one."""
    try:
        return destination_root / path.relative_to(source_root)
    except ValueError:
        return None


def export_workspace(destination: Path) -> Path:
    """Export portable workspace metadata without challenge files or secrets."""
    import copy

    from pwnv.utils.config import load_config

    destination = destination.expanduser().resolve()
    if destination.suffix.lower() != ".json":
        destination = destination.with_suffix(".json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    exported = copy.deepcopy(load_config())
    for challenge in exported.get("challenges", []):
        challenge["flag"] = None
        extras = challenge.get("extras")
        if isinstance(extras, dict):
            extras.pop("flag_history", None)
    destination.write_text(
        json.dumps(exported, indent=4, default=str), encoding="utf-8"
    )
    return destination


def import_workspace(source: Path, *, replace: bool = False) -> dict[str, int]:
    """
    Import metadata, rebasing all workspace paths to the current CTF root.

    By default the import is *merged* into the current workspace: CTFs and
    challenges already present are left alone and only new records are added,
    so importing a teammate's export cannot discard your own solves. Pass
    ``replace=True`` for the previous behaviour of overwriting everything.

    Returns a summary of how many records were added and skipped.
    """
    from pwnv.utils.config import get_ctfs_path

    data = json.loads(source.expanduser().resolve().read_text(encoding="utf-8"))
    imported = Init.model_validate(data)
    ctfs_path = get_ctfs_path().resolve()
    _rebase_by_name(imported, ctfs_path)
    imported.ctfs_path = ctfs_path
    return _merge_records(imported, replace=replace)


def _rebase_by_name(imported: Init, ctfs_path: Path) -> None:
    """
    Point every record at the directory its name implies under ``ctfs_path``.

    An export carries no files, so there is no layout to preserve: the
    directories are recreated from the names, exactly as ``pwnv ctf add`` would.
    """
    from pwnv.utils.remote import sanitize

    ctf_paths: dict = {}
    for ctf in imported.ctfs:
        if ctf is None:
            continue
        ctf.path = ctfs_path / sanitize(ctf.name)
        ctf.path.mkdir(parents=True, exist_ok=True)
        ctf_paths[ctf.id] = ctf.path

    for challenge in imported.challenges:
        if challenge is None or challenge.ctf_id not in ctf_paths:
            continue
        challenge.path = (
            ctf_paths[challenge.ctf_id]
            / challenge.category.name
            / sanitize(challenge.name)
        )
        challenge.path.mkdir(parents=True, exist_ok=True)


def _merge_records(imported: Init, *, replace: bool) -> dict[str, int]:
    """Fold ``imported`` into the stored configuration, skipping duplicates."""
    from pwnv.utils.config import config_transaction

    summary = {
        "ctfs_added": 0,
        "ctfs_skipped": 0,
        "challenges_added": 0,
        "challenges_skipped": 0,
    }

    if replace:
        from pwnv.utils.config import save_config

        payload = imported.model_dump()
        summary["ctfs_added"] = len(payload.get("ctfs", []))
        summary["challenges_added"] = len(payload.get("challenges", []))
        save_config(payload)
        return summary

    incoming = imported.model_dump()
    with config_transaction() as cfg:
        existing_ctfs = cfg.setdefault("ctfs", [])
        existing_challenges = cfg.setdefault("challenges", [])
        known_ctf_ids = {str(item["id"]) for item in existing_ctfs}
        known_ctf_names = {item["name"] for item in existing_ctfs}
        known_challenge_ids = {str(item["id"]) for item in existing_challenges}
        known_challenge_paths = {str(item["path"]) for item in existing_challenges}

        for ctf_data in incoming.get("ctfs", []):
            if (
                str(ctf_data["id"]) in known_ctf_ids
                or ctf_data["name"] in known_ctf_names
            ):
                summary["ctfs_skipped"] += 1
                continue
            existing_ctfs.append(ctf_data)
            known_ctf_ids.add(str(ctf_data["id"]))
            known_ctf_names.add(ctf_data["name"])
            summary["ctfs_added"] += 1

        for challenge_data in incoming.get("challenges", []):
            if (
                str(challenge_data["id"]) in known_challenge_ids
                or str(challenge_data["path"]) in known_challenge_paths
                or str(challenge_data["ctf_id"]) not in known_ctf_ids
            ):
                summary["challenges_skipped"] += 1
                continue
            existing_challenges.append(challenge_data)
            known_challenge_ids.add(str(challenge_data["id"]))
            known_challenge_paths.add(str(challenge_data["path"]))
            summary["challenges_added"] += 1

        cfg["challenge_tags"] = sorted(
            set(cfg.get("challenge_tags", [])) | set(incoming.get("challenge_tags", []))
        )

    return summary
