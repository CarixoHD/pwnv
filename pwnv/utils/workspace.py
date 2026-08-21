"""Backup and portability helpers for pwnv workspaces."""

import json
import tarfile
from pathlib import Path

from pwnv.constants import DEFAULT_PWNVENV_FOLDER_NAME
from pwnv.models import Init


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
            if DEFAULT_PWNVENV_FOLDER_NAME in path.parts:
                continue
            archive.add(
                path,
                arcname=Path("ctfs") / path.relative_to(ctfs_path),
                recursive=False,
            )
    return destination


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


def import_workspace(source: Path) -> None:
    """Import metadata, rebasing all workspace paths to the current CTF root."""
    from pwnv.utils.config import get_ctfs_path, save_config

    data = json.loads(source.expanduser().resolve().read_text(encoding="utf-8"))
    imported = Init.model_validate(data)
    ctfs_path = get_ctfs_path().resolve()
    ctf_paths = {}

    from pwnv.utils.remote import sanitize

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

    imported.ctfs_path = ctfs_path
    save_config(imported.model_dump())
