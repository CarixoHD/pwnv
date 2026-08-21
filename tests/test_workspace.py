import json
import tarfile

from pwnv.models import CTF, Challenge
from pwnv.models.challenge import Category
from pwnv.utils import (
    add_challenge,
    add_ctf,
    backup_workspace,
    export_workspace,
    get_challenges,
    get_config_path,
    get_ctfs,
    get_ctfs_path,
    import_workspace,
    save_config,
)


def _create_workspace(tmp_path):
    ctf = CTF(name="Example CTF", path=get_ctfs_path() / "example-ctf")
    challenge = Challenge(
        name="Web Challenge",
        ctf_id=ctf.id,
        path=ctf.path / "web" / "challenge",
        category=Category.web,
    )
    add_ctf(ctf)
    add_challenge(challenge)
    (challenge.path / "notes.txt").write_text("work", encoding="utf-8")
    return ctf, challenge


def test_backup_contains_config_and_challenge_files(tmp_path):
    _create_workspace(tmp_path)

    backup = backup_workspace(tmp_path / "backup")

    with tarfile.open(backup) as archive:
        names = archive.getnames()
    assert f"config/{get_config_path().name}" in names
    assert "ctfs/example-ctf/web/challenge/notes.txt" in names


def test_export_and_import_rebase_paths(tmp_path):
    _create_workspace(tmp_path)
    exported = export_workspace(tmp_path / "workspace")
    current_ctfs_path = get_ctfs_path()

    data = json.loads(exported.read_text(encoding="utf-8"))
    assert data["ctfs"][0]["name"] == "Example CTF"

    save_config(
        {
            "ctfs_path": current_ctfs_path,
            "challenge_tags": [],
            "ctfs": [],
            "challenges": [],
        }
    )
    import_workspace(exported)

    imported_ctf = get_ctfs()[0]
    imported_challenge = get_challenges()[0]
    assert imported_ctf.path == current_ctfs_path / "example-ctf"
    assert imported_challenge.path == imported_ctf.path / "web" / "web-challenge"
    assert imported_challenge.path.is_dir()
