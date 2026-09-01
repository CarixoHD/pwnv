"""Regression tests for defects that would bite during a live CTF."""

import json
import tarfile
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from pwnv import app
from pwnv.models import CTF, Challenge
from pwnv.models.challenge import Category, Solved
from pwnv.utils import (
    add_challenge,
    add_ctf,
    get_challenges,
    get_ctfs,
    get_ctfs_path,
)


def _remote_workspace():
    """A CTF with a remote URL and one unsolved challenge."""
    ctf = CTF(
        name="RemoteCTF", path=get_ctfs_path() / "remotectf", url="https://ctf.invalid"
    )
    add_ctf(ctf)
    challenge = Challenge(
        name="Baby ROP",
        ctf_id=ctf.id,
        path=ctf.path / "pwn" / "baby-rop",
        category=Category.pwn,
        points=100,
        extras={"slug": "42"},
    )
    add_challenge(challenge)
    return ctf, challenge


def test_rejected_flag_does_not_mark_challenge_solved(monkeypatch):
    """A flag the platform rejects must not be recorded as a solve."""
    import pwnv.utils as utils

    _remote_workspace()

    async def _reject(**_kwargs):
        return False

    monkeypatch.setattr(utils, "remote_solve", _reject)

    result = CliRunner().invoke(
        app,
        [
            "solve",
            "--flag",
            "FLAG{wrong}",
            "--challenge",
            "Baby ROP",
            "--ctf",
            "RemoteCTF",
            "--tags",
            "",
        ],
    )

    # Non-zero exit so `pwnv solve ... && echo solved` cannot lie.
    assert result.exit_code == 1
    challenge = get_challenges()[0]
    assert challenge.solved == Solved.unsolved
    assert challenge.flag is None
    # The attempt is still recorded for --history.
    assert len(challenge.extras["flag_history"]) == 1
    assert challenge.extras["flag_history"][0]["result"] == "rejected-or-failed"


def test_challenge_remains_solvable_after_a_rejected_flag(monkeypatch):
    """A typo must not lock the challenge out of `pwnv solve` forever."""
    import pwnv.utils as utils

    _remote_workspace()

    async def _reject(**_kwargs):
        return False

    monkeypatch.setattr(utils, "remote_solve", _reject)
    CliRunner().invoke(
        app,
        ["solve", "--flag", "FLAG{wrong}", "--challenge", "Baby ROP", "--tags", ""],
    )

    async def _accept(**_kwargs):
        return True

    monkeypatch.setattr(utils, "remote_solve", _accept)
    result = CliRunner().invoke(
        app,
        ["solve", "--flag", "FLAG{right}", "--challenge", "Baby ROP", "--tags", "rop"],
    )

    assert result.exit_code == 0
    challenge = get_challenges()[0]
    assert challenge.solved == Solved.solved
    assert challenge.flag == "FLAG{right}"
    assert len(challenge.extras["flag_history"]) == 2


def test_guard_failure_exits_non_zero():
    """Guards must fail the process, not print a warning and return success."""
    from pwnv.utils.guards import _guard

    guarded = _guard(lambda: False, "nothing here")(lambda: "ran")

    with pytest.raises(typer.Exit) as excinfo:
        guarded()
    assert excinfo.value.exit_code == 1


def test_reset_only_removes_pwnv_artifacts():
    """`pwnv reset` must never rmtree the config file's parent directory."""
    from pwnv.utils import get_config_path

    config_dir = get_config_path().parent
    bystander = config_dir / "unrelated_notes.txt"
    bystander.write_text("hard-won exploit notes", encoding="utf-8")
    documents = config_dir / "Documents"
    documents.mkdir()

    result = CliRunner().invoke(app, ["reset", "--force"])

    assert result.exit_code == 0
    assert config_dir.is_dir()
    assert bystander.is_file()
    assert documents.is_dir()
    assert not get_config_path().exists()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("pwn", Category.pwn),
        ("Binary Exploitation", Category.pwn),
        ("Pwn (Beginner)", Category.pwn),
        ("(Web) Exploitation", Category.web),
        ("Web Exploitation", Category.web),
        ("Reversing", Category.rev),
        ("RE", Category.rev),
        ("Reverse Engineering", Category.rev),
        ("Forensic", Category.forensics),
        ("DFIR", Category.forensics),
        ("Smart Contracts", Category.blockchain),
        ("Steg", Category.steg),
        ("Mobile - Android", Category.mobile),
        ("Cryptography", Category.crypto),
        ("misc/warmup", Category.misc),
        ("", Category.other),
        ("Networking", Category.other),
    ],
)
def test_category_normalisation(raw, expected):
    """Real-world platform category labels map to the right Category."""
    from pwnv.utils import normalise_category

    assert normalise_category(raw) == expected


def test_sync_keeps_the_platform_challenge_name():
    """The scoreboard name must survive sync; only the directory is sanitized."""
    import asyncio
    from types import SimpleNamespace

    from pwnv.utils.remote import add_remote_challenges

    ctf = CTF(name="SyncCTF", path=get_ctfs_path() / "syncctf", url="https://x.invalid")
    add_ctf(ctf)

    remote_challenge = SimpleNamespace(
        id="chal-1",
        name="Baby ROP",
        category="pwn",
        value=100,
        solved=False,
        description="Overflow it",
        author="admin",
        tags=[],
        attachments=[],
        services=[],
    )

    class _Attachments:
        async def download_all(self, ch, save_dir):
            return ch

    client = SimpleNamespace(attachments=_Attachments())
    asyncio.run(add_remote_challenges(client, ctf, [remote_challenge]))

    challenge = get_challenges()[0]
    assert challenge.name == "Baby ROP"
    assert challenge.path.name == "baby-rop"


def test_backup_excludes_challenge_virtualenvs(tmp_path):
    """Generated venvs must not be archived into every backup."""
    from pwnv.utils import backup_workspace

    ctf = CTF(name="VenvCTF", path=get_ctfs_path() / "venvctf")
    add_ctf(ctf)
    challenge = Challenge(
        name="chal",
        ctf_id=ctf.id,
        path=ctf.path / "pwn" / "chal",
        category=Category.pwn,
    )
    add_challenge(challenge)

    (challenge.path / "solve.py").write_text("print('solve')", encoding="utf-8")
    venv_bin = challenge.path / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    (venv_bin / "python").write_text("binary", encoding="utf-8")
    shared_env = get_ctfs_path() / ".pwnvenv" / "bin"
    shared_env.mkdir(parents=True)
    (shared_env / "python").write_text("binary", encoding="utf-8")

    archive_path = backup_workspace(tmp_path / "backup")
    with tarfile.open(archive_path) as archive:
        names = archive.getnames()

    assert any(name.endswith("solve.py") for name in names)
    assert not any(".venv" in name for name in names)
    assert not any(".pwnvenv" in name for name in names)


def test_import_merges_instead_of_discarding_local_work(tmp_path):
    """Importing a teammate's export must not delete your own CTFs."""
    from pwnv.utils import import_workspace

    mine = CTF(name="MyCTF", path=get_ctfs_path() / "myctf")
    add_ctf(mine)
    add_challenge(
        Challenge(
            name="my-chal",
            ctf_id=mine.id,
            path=mine.path / "pwn" / "my-chal",
            category=Category.pwn,
            solved=Solved.solved,
        )
    )

    teammate = {
        "ctfs_path": str(get_ctfs_path()),
        "challenge_tags": ["rop"],
        "ctfs": [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "name": "TheirCTF",
                "created_at": "2026-01-01T00:00:00",
                "path": "/somewhere/else/theirctf",
                "running": 1,
                "url": None,
            }
        ],
        "challenges": [
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "name": "their-chal",
                "flag": None,
                "points": 50,
                "solved": 0,
                "category": 2,
                "ctf_id": "11111111-1111-1111-1111-111111111111",
                "path": "/somewhere/else/theirctf/web/their-chal",
                "tags": [],
                "extras": None,
            }
        ],
    }
    export_file = tmp_path / "theirs.json"
    export_file.write_text(json.dumps(teammate), encoding="utf-8")

    summary = import_workspace(export_file)

    names = {ctf.name for ctf in get_ctfs()}
    assert names == {"MyCTF", "TheirCTF"}
    assert summary["ctfs_added"] == 1
    assert summary["challenges_added"] == 1
    # Local work is untouched and the imported challenge is rebased locally.
    challenges = {ch.name: ch for ch in get_challenges()}
    assert challenges["my-chal"].solved == Solved.solved
    assert challenges["their-chal"].path.is_relative_to(get_ctfs_path())
    # Importing the same export twice is a no-op rather than a duplication.
    again = import_workspace(export_file)
    assert again["ctfs_added"] == 0
    assert again["challenges_added"] == 0
    assert len(get_ctfs()) == 2


def test_import_replace_still_available(tmp_path):
    """`--replace` keeps the old destructive behaviour when asked for."""
    from pwnv.utils import export_workspace, import_workspace

    add_ctf(CTF(name="Original", path=get_ctfs_path() / "original"))
    export_file = export_workspace(tmp_path / "snapshot.json")

    add_ctf(CTF(name="AddedLater", path=get_ctfs_path() / "addedlater"))
    assert len(get_ctfs()) == 2

    import_workspace(export_file, replace=True)

    assert {ctf.name for ctf in get_ctfs()} == {"Original"}


def test_current_challenge_resolves_after_a_directory_change(monkeypatch):
    """Challenge lookup must use the live cwd, not the one frozen at import."""
    from pwnv.utils import crud

    ctf = CTF(name="CwdCTF", path=get_ctfs_path() / "cwdctf")
    add_ctf(ctf)
    challenge = Challenge(
        name="chal",
        ctf_id=ctf.id,
        path=ctf.path / "pwn" / "chal",
        category=Category.pwn,
    )
    add_challenge(challenge)
    nested = challenge.path / "build" / "obj"
    nested.mkdir(parents=True)

    monkeypatch.chdir(nested)

    assert crud.get_current_challenge() is not None
    assert crud.get_current_challenge().name == "chal"
    assert crud.get_current_ctf().name == "CwdCTF"


def test_config_transaction_reads_fresh_state_under_the_lock():
    """A transaction must not build on a stale cached read."""
    from pwnv.utils.config import config_transaction, get_config_path, load_config

    load_config()  # prime the lru_cache

    # Simulate another pwnv process writing while our cache is warm.
    raw = json.loads(get_config_path().read_text(encoding="utf-8"))
    raw["challenge_tags"] = ["written-by-another-process"]
    get_config_path().write_text(json.dumps(raw), encoding="utf-8")

    with config_transaction() as cfg:
        assert cfg["challenge_tags"] == ["written-by-another-process"]
        cfg["challenge_tags"].append("mine")

    assert set(load_config()["challenge_tags"]) == {
        "written-by-another-process",
        "mine",
    }


def test_corrupt_config_reports_cleanly_instead_of_traceback():
    """A truncated config must produce a readable error, not a JSONDecodeError."""
    from pwnv.utils.config import get_config_path, _invalidate_cache, load_config

    get_config_path().write_text('{"ctfs": [', encoding="utf-8")
    _invalidate_cache()

    with pytest.raises(typer.Exit) as excinfo:
        load_config()
    assert excinfo.value.exit_code == 1


def test_expired_session_is_retried_with_stored_credentials(tmp_path, monkeypatch):
    """A session that goes stale mid-event must re-login, not just fail."""
    from pwnv.utils import remote as remote_mod

    ctf = CTF(
        name="StaleCTF", path=get_ctfs_path() / "stalectf", url="https://x.invalid"
    )
    add_ctf(ctf)
    ctf.path.mkdir(parents=True, exist_ok=True)
    (ctf.path / ".env").write_text(
        "CTF_USERNAME=player\nCTF_PASSWORD=hunter2\n", encoding="utf-8"
    )

    calls = {"fetch": 0, "login": 0}

    def _fake_fetch(client, ctf_arg):
        calls["fetch"] += 1
        # First fetch fails as an expired cookie would; the retry succeeds.
        return None if calls["fetch"] == 1 else []

    async def _fetch(client, ctf_arg):
        return _fake_fetch(client, ctf_arg)

    async def _login(client, creds, ctf_arg):
        calls["login"] += 1
        assert creds["username"] == "player"
        return True

    async def _methods(url):
        return object(), ["credentials"]

    monkeypatch.setattr(remote_mod, "get_remote_challenges", _fetch)
    monkeypatch.setattr(remote_mod, "create_remote_session", _login)
    monkeypatch.setattr(remote_mod, "get_remote_credential_methods", _methods)

    assert remote_mod.sync_remote_ctf(ctf) is not None
    # One login for the initial .env auth, one for the expiry retry.
    assert calls["login"] == 2
    assert calls["fetch"] == 2


def test_ctf_directory_gets_a_gitignore_for_secrets():
    """Credentials and cookie jars must not be committable by accident."""
    from pwnv.utils.remote import protect_ctf_secrets

    ctf = CTF(name="ShareCTF", path=get_ctfs_path() / "sharectf")
    add_ctf(ctf)
    protect_ctf_secrets(ctf.path)

    entries = (ctf.path / ".gitignore").read_text(encoding="utf-8").split()
    assert ".env" in entries
    assert ".session" in entries

    # Running again is idempotent and preserves anything already there.
    (ctf.path / ".gitignore").write_text("custom-entry\n", encoding="utf-8")
    protect_ctf_secrets(ctf.path)
    entries = (ctf.path / ".gitignore").read_text(encoding="utf-8").split()
    assert "custom-entry" in entries
    assert ".env" in entries


def test_plugin_module_does_not_shadow_stdlib(tmp_path):
    """A plugin named after a stdlib module must not hijack that import."""
    import sys

    from pwnv.core.plugin_manager import PluginManager, plugin_name
    from pwnv.utils.plugin import get_plugins_directory

    plugins_dir = get_plugins_directory()
    (plugins_dir / "json.py").write_text(
        "from pwnv.core import register_plugin\n"
        "from pwnv.models.challenge import Category\n"
        "from pwnv.plugins.plugin import ChallengePlugin\n"
        "\n"
        "@register_plugin\n"
        "class ShadowPlugin(ChallengePlugin):\n"
        "    def category(self):\n"
        "        return Category.misc\n"
        "    def logic(self, challenge):\n"
        "        ...\n",
        encoding="utf-8",
    )

    manager = PluginManager()
    manager.discover_and_load_plugins()

    # The real stdlib json is still importable and intact.
    import json as json_module

    assert sys.modules["json"] is json_module
    assert hasattr(json_module, "dumps")

    loaded = [p for p in manager.get_all_plugins() if plugin_name(p) == "json"]
    assert loaded, "the plugin should still load under its own name"


def test_local_challenge_flag_submission_reports_missing_remote_id(monkeypatch):
    """A locally-created challenge explains itself instead of failing mutely."""
    import asyncio

    from pwnv.utils.remote import remote_solve

    ctf = CTF(
        name="MixedCTF", path=get_ctfs_path() / "mixedctf", url="https://x.invalid"
    )
    add_ctf(ctf)
    local = Challenge(
        name="hand-made",
        ctf_id=ctf.id,
        path=ctf.path / "pwn" / "hand-made",
        category=Category.pwn,
    )
    add_challenge(local)

    def _no_client(url):  # pragma: no cover - must never be reached
        raise AssertionError("a client must not be created for a local challenge")

    monkeypatch.setattr("ctfbridge.create_client", _no_client)
    assert asyncio.run(remote_solve(ctf=ctf, challenge=local, flag="FLAG{x}")) is False


def test_sync_keeps_challenges_whose_names_sanitize_identically():
    """Distinct platform challenges must not collapse into one record."""
    import asyncio
    from types import SimpleNamespace

    from pwnv.utils.remote import add_remote_challenges

    ctf = CTF(name="CollideCTF", path=get_ctfs_path() / "collide", url="https://x.inv")
    add_ctf(ctf)

    def _remote(index, name):
        return SimpleNamespace(
            id=f"id-{index}",
            name=name,
            category="pwn",
            value=100,
            solved=False,
            description=f"desc {index}",
            author=None,
            tags=[],
            attachments=[],
            services=[],
        )

    class _Attachments:
        async def download_all(self, ch, save_dir):
            return ch

    client = SimpleNamespace(attachments=_Attachments())
    remote = [_remote(1, "Baby ROP"), _remote(2, "baby rop"), _remote(3, "Baby  ROP")]
    asyncio.run(add_remote_challenges(client, ctf, remote))

    challenges = get_challenges()
    assert len(challenges) == 3
    assert {ch.extras["slug"] for ch in challenges} == {"id-1", "id-2", "id-3"}
    # Each gets its own directory rather than sharing one.
    assert len({ch.path for ch in challenges}) == 3

    # Re-syncing matches on the remote id, so nothing is duplicated.
    asyncio.run(add_remote_challenges(client, ctf, remote))
    assert len(get_challenges()) == 3


def test_local_ctf_ignores_ambient_platform_credentials(monkeypatch):
    """Exported PWNV_CTF_* must not block `ctf add --local`."""
    monkeypatch.setenv("PWNV_CTF_USERNAME", "player")
    monkeypatch.setenv("PWNV_CTF_PASSWORD", "hunter2")

    result = CliRunner().invoke(app, ["ctf", "add", "OfflineCTF", "--local"])

    assert result.exit_code == 0
    assert "OfflineCTF" in {ctf.name for ctf in get_ctfs()}


def test_empty_selector_reports_instead_of_raising():
    """An empty candidate list must not surface InquirerPy's InvalidArgument."""
    from pwnv.utils.ui import prompt_challenge_selection

    with pytest.raises(typer.Exit) as excinfo:
        prompt_challenge_selection([], "Select a challenge:")
    assert excinfo.value.exit_code == 1


def test_remove_commands_are_scriptable():
    """`--yes` lets removal run unattended."""
    ctf = CTF(name="ScriptCTF", path=get_ctfs_path() / "scriptctf")
    add_ctf(ctf)
    challenge = Challenge(
        name="doomed",
        ctf_id=ctf.id,
        path=ctf.path / "pwn" / "doomed",
        category=Category.pwn,
    )
    add_challenge(challenge)
    (challenge.path / "solve.py").write_text("x", encoding="utf-8")

    removed = CliRunner().invoke(
        app, ["challenge", "remove", "--challenge", "doomed", "--yes"]
    )
    assert removed.exit_code == 0
    assert get_challenges() == []

    removed_ctf = CliRunner().invoke(app, ["ctf", "remove", "--ctf", "ScriptCTF", "-y"])
    assert removed_ctf.exit_code == 0
    assert get_ctfs() == []


def test_search_with_only_a_scope_lists_that_scope():
    """`challenge search --ctf X` must list X, not return nothing."""
    ctf = CTF(name="ScopeCTF", path=get_ctfs_path() / "scopectf")
    add_ctf(ctf)
    add_challenge(
        Challenge(
            name="listed",
            ctf_id=ctf.id,
            path=ctf.path / "pwn" / "listed",
            category=Category.pwn,
        )
    )
    other = CTF(name="OtherCTF", path=get_ctfs_path() / "otherctf")
    add_ctf(other)
    add_challenge(
        Challenge(
            name="elsewhere",
            ctf_id=other.id,
            path=other.path / "web" / "elsewhere",
            category=Category.web,
        )
    )

    result = CliRunner().invoke(app, ["challenge", "search", "--ctf", "ScopeCTF"])

    assert result.exit_code == 0
    assert "listed" in result.output
    assert "elsewhere" not in result.output


def _teammate_export(ctf_name: str, ctf_id: str, challenge_name: str) -> dict:
    """An export as another machine would write it, rooted somewhere else."""
    return {
        "ctfs_path": "/somewhere/else",
        "challenge_tags": [],
        "ctfs": [
            {
                "id": ctf_id,
                "name": ctf_name,
                "created_at": "2026-01-01T00:00:00",
                "path": f"/somewhere/else/{ctf_name.lower()}",
                "running": 1,
                "url": None,
            }
        ],
        "challenges": [
            {
                "id": "33333333-3333-3333-3333-333333333333",
                "name": challenge_name,
                "flag": None,
                "points": 50,
                "solved": 0,
                "category": 2,
                "ctf_id": ctf_id,
                "path": f"/somewhere/else/{ctf_name.lower()}/web/{challenge_name}",
                "tags": [],
                "extras": None,
            }
        ],
    }


def test_import_adopts_challenges_of_a_ctf_already_in_the_workspace(tmp_path):
    """
    Two people at the same event have the same CTF under two different ids.

    The CTF is skipped as a duplicate, and its challenges used to be skipped
    with it - they referred to an id this config had never heard of - so the
    import silently added nothing at all.
    """
    from pwnv.utils import import_workspace

    mine = CTF(name="SharedCTF", path=get_ctfs_path() / "sharedctf")
    add_ctf(mine)

    export_file = tmp_path / "theirs.json"
    export_file.write_text(
        json.dumps(
            _teammate_export(
                "SharedCTF", "44444444-4444-4444-4444-444444444444", "their-chal"
            )
        ),
        encoding="utf-8",
    )

    summary = import_workspace(export_file)

    assert summary["ctfs_skipped"] == 1
    assert summary["challenges_added"] == 1
    challenges = get_challenges()
    assert [ch.name for ch in challenges] == ["their-chal"]
    # Adopted by the CTF that was already here, not by the id in the export.
    assert challenges[0].ctf_id == mine.id


def _backup_from_another_machine(tmp_path, old_root: str) -> Path:
    """Write an archive whose config was recorded under ``old_root``."""
    config = {
        "ctfs_path": old_root,
        "challenge_tags": [],
        "ctfs": [
            {
                "id": "55555555-5555-5555-5555-555555555555",
                "name": "OldCTF",
                "created_at": "2026-01-01T00:00:00",
                "path": f"{old_root}/oldctf",
                "running": 1,
                "url": None,
            }
        ],
        "challenges": [
            {
                "id": "66666666-6666-6666-6666-666666666666",
                "name": "chal",
                "flag": None,
                "points": 50,
                "solved": 0,
                "category": 2,
                "ctf_id": "55555555-5555-5555-5555-555555555555",
                "path": f"{old_root}/oldctf/web/chal",
                "tags": [],
                "extras": {
                    "attachments": [
                        {
                            "name": "vuln",
                            "local_path": f"{old_root}/oldctf/web/chal/vuln",
                        }
                    ]
                },
            }
        ],
    }

    staged = tmp_path / "staged"
    (staged / "config").mkdir(parents=True)
    (staged / "config" / "pwnv_config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    challenge_dir = staged / "ctfs" / "oldctf" / "web" / "chal"
    challenge_dir.mkdir(parents=True)
    (challenge_dir / "vuln").write_text("ELF", encoding="utf-8")

    archive = tmp_path / "backup.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(staged / "config", arcname="config")
        tar.add(staged / "ctfs", arcname="ctfs")
    return archive


def test_restore_rebases_downloaded_attachments(tmp_path):
    """An attachment must point at the copy that travelled with the archive."""
    from pwnv.utils import restore_workspace

    archive = _backup_from_another_machine(tmp_path, "/old/machine/CTFs")

    restore_workspace(archive)

    challenge = get_challenges()[0]
    local = Path(challenge.extras["attachments"][0]["local_path"])
    assert local.is_relative_to(get_ctfs_path())
    assert local.read_text(encoding="utf-8") == "ELF"


def test_restoring_something_that_is_not_an_archive_reports_cleanly(tmp_path):
    """A wrong file must produce a message, not a tarfile traceback."""
    bogus = tmp_path / "notes.tar.gz"
    bogus.write_text("these are notes, not a tarball", encoding="utf-8")

    result = CliRunner().invoke(app, ["workspace", "restore", str(bogus)])

    assert result.exit_code == 1
    assert not isinstance(result.exception, tarfile.TarError)
    assert "could not be read" in result.output
