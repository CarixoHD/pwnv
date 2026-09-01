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
    restore_workspace,
    save_config,
    update_challenge,
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


def test_backup_does_not_include_itself(tmp_path):
    _create_workspace(tmp_path)
    destination = get_ctfs_path() / "workspace-backup"

    backup = backup_workspace(destination)

    with tarfile.open(backup) as archive:
        assert "ctfs/workspace-backup.tar.gz" not in archive.getnames()


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


def test_export_removes_flags_and_submission_history(tmp_path):
    _, challenge = _create_workspace(tmp_path)
    challenge.flag = "FLAG{secret}"
    challenge.extras = {
        "description": "safe metadata",
        "flag_history": [{"flag": "FLAG{attempt}"}],
    }
    update_challenge(challenge)

    exported = export_workspace(tmp_path / "shareable")
    data = json.loads(exported.read_text(encoding="utf-8"))

    assert data["challenges"][0]["flag"] is None
    assert "flag_history" not in data["challenges"][0]["extras"]
    assert data["challenges"][0]["extras"]["description"] == "safe metadata"


def _fresh_machine(tmp_path, name: str = "new-machine"):
    """Point the workspace at an empty CTF root, as a new install would be."""
    ctfs_path = tmp_path / name
    ctfs_path.mkdir(parents=True, exist_ok=True)
    save_config(
        {
            "ctfs_path": str(ctfs_path),
            "challenge_tags": [],
            "ctfs": [],
            "challenges": [],
        }
    )
    return ctfs_path


def test_restore_puts_the_files_back_under_the_new_ctf_root(tmp_path):
    """The move-to-a-new-PC path: backup here, restore against another root."""
    _, challenge = _create_workspace(tmp_path)
    (challenge.path / "solve.py").write_text("print('pwn')", encoding="utf-8")
    backup = backup_workspace(tmp_path / "backup")

    ctfs_path = _fresh_machine(tmp_path)
    summary = restore_workspace(backup)

    restored_ctf = get_ctfs()[0]
    restored_challenge = get_challenges()[0]
    assert restored_ctf.path == ctfs_path / "example-ctf"
    assert restored_challenge.path == ctfs_path / "example-ctf" / "web" / "challenge"
    assert (restored_challenge.path / "notes.txt").read_text() == "work"
    assert (restored_challenge.path / "solve.py").read_text() == "print('pwn')"
    assert summary["files_restored"] == 2
    assert summary["ctfs_added"] == 1


def test_restore_keeps_the_directory_names_the_backup_used(tmp_path):
    """Names are recomputed on import; a backup has real directories to keep."""
    ctf = CTF(name="Example CTF", path=get_ctfs_path() / "example-ctf")
    challenge = Challenge(
        name="Web Challenge",
        ctf_id=ctf.id,
        # `_unique_challenge_path` produces suffixes like this on a name clash.
        path=ctf.path / "web" / "web-challenge_2",
        category=Category.web,
    )
    add_ctf(ctf)
    add_challenge(challenge)
    (challenge.path / "flagged.txt").write_text("keep", encoding="utf-8")
    backup = backup_workspace(tmp_path / "backup")

    ctfs_path = _fresh_machine(tmp_path)
    restore_workspace(backup)

    restored = get_challenges()[0]
    assert restored.path == ctfs_path / "example-ctf" / "web" / "web-challenge_2"
    assert (restored.path / "flagged.txt").is_file()


def test_restore_keeps_credentials_that_a_plain_export_drops(tmp_path):
    ctf, challenge = _create_workspace(tmp_path)
    (ctf.path / ".env").write_text("PWNV_CTF_TOKEN=secret", encoding="utf-8")
    challenge.flag = "FLAG{kept}"
    update_challenge(challenge)
    backup = backup_workspace(tmp_path / "backup")

    ctfs_path = _fresh_machine(tmp_path)
    restore_workspace(backup)

    assert (ctfs_path / "example-ctf" / ".env").read_text() == "PWNV_CTF_TOKEN=secret"
    assert get_challenges()[0].flag == "FLAG{kept}"


def test_restore_leaves_local_work_alone_unless_forced(tmp_path):
    _, challenge = _create_workspace(tmp_path)
    backup = backup_workspace(tmp_path / "backup")

    challenge.path.mkdir(parents=True, exist_ok=True)
    (challenge.path / "notes.txt").write_text("newer work", encoding="utf-8")
    restore_workspace(backup)
    assert (challenge.path / "notes.txt").read_text() == "newer work"

    summary = restore_workspace(backup, force=True)
    assert (challenge.path / "notes.txt").read_text() == "work"
    assert summary["files_restored"] == 1


def test_restore_re_run_adds_nothing_the_second_time(tmp_path):
    _create_workspace(tmp_path)
    backup = backup_workspace(tmp_path / "backup")
    _fresh_machine(tmp_path)

    restore_workspace(backup)
    again = restore_workspace(backup)

    assert again["ctfs_added"] == 0
    assert again["challenges_added"] == 0
    assert again["ctfs_skipped"] == 1
    assert len(get_ctfs()) == 1


def test_restore_rejects_an_archive_that_is_not_a_backup(tmp_path):
    import pytest

    not_a_backup = tmp_path / "random.tar.gz"
    with tarfile.open(not_a_backup, "w:gz") as archive:
        payload = tmp_path / "hello.txt"
        payload.write_text("hi", encoding="utf-8")
        archive.add(payload, arcname="hello.txt")

    with pytest.raises(ValueError, match="not look like a pwnv backup"):
        restore_workspace(not_a_backup)

    with pytest.raises(FileNotFoundError):
        restore_workspace(tmp_path / "missing.tar.gz")
