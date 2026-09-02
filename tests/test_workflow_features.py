import asyncio
import json
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from pwnv import app
from pwnv.models import CTF, Challenge
from pwnv.models.challenge import Category, Solved
from pwnv.models.ctf import Status
from pwnv.utils import (
    add_challenge,
    add_ctf,
    get_challenges,
    get_ctfs_path,
)


def _ctf(name: str, *, running: Status = Status.running, url: str | None = None) -> CTF:
    ctf = CTF(
        name=name,
        path=get_ctfs_path() / name.lower(),
        running=running,
        url=url,
    )
    add_ctf(ctf)
    return ctf


def _challenge(ctf: CTF, name: str, category: Category = Category.pwn, **kwargs):
    challenge = Challenge(
        name=name,
        ctf_id=ctf.id,
        path=ctf.path / category.name / name.lower().replace(" ", "-"),
        category=category,
        **kwargs,
    )
    add_challenge(challenge)
    return challenge


def _install_plugin(category: Category, name: str, marker: str) -> None:
    from pwnv.core.plugin_manager import plugin_manager
    from pwnv.utils.plugin import (
        get_plugins_directory,
        get_templates_directory,
        set_selected_plugin_for_category,
    )

    source = textwrap.dedent(
        f"""
        from pwnv.core import register_plugin
        from pwnv.models.challenge import Category
        from pwnv.plugins.plugin import ChallengePlugin

        @register_plugin
        class {name.capitalize()}Plugin(ChallengePlugin):
            def category(self):
                return Category.{category.name}

            def logic(self, challenge):
                (challenge.path / "{name}.ran").touch()
        """
    )
    (get_plugins_directory() / f"{name}.py").write_text(source, encoding="utf-8")

    template_dir = get_templates_directory() / category.name
    template_dir.mkdir(parents=True, exist_ok=True)
    (template_dir / "solve.py").write_text(
        f"# {marker} {{{{challenge.name}}}}\n", encoding="utf-8"
    )

    plugin_manager._loaded = False  # type: ignore[attr-defined]
    plugin_manager.get_all_plugins.cache_clear()  # type: ignore[attr-defined]
    set_selected_plugin_for_category(category, name)


def _runner() -> CliRunner:
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:  # click >= 8.2 never mixes them
        return CliRunner()


def test_scaffold_writes_the_template_and_runs_plugin_logic():
    ctf = _ctf("ScaffoldCTF")
    challenge = _challenge(ctf, "Baby ROP")
    _install_plugin(Category.pwn, "pwnplug", "PWN")

    result = CliRunner().invoke(
        app, ["challenge", "scaffold", "--challenge", "Baby ROP", "--category", "pwn"]
    )

    assert result.exit_code == 0
    assert (challenge.path / "solve.py").read_text() == "# PWN Baby ROP\n"
    assert (challenge.path / "pwnplug.ran").exists()


def test_scaffold_never_overwrites_work_in_progress():
    ctf = _ctf("ScaffoldCTF")
    challenge = _challenge(ctf, "Baby ROP")
    _install_plugin(Category.pwn, "pwnplug", "PWN")
    challenge.path.mkdir(parents=True, exist_ok=True)
    (challenge.path / "solve.py").write_text("MY EXPLOIT", encoding="utf-8")

    result = CliRunner().invoke(
        app, ["challenge", "scaffold", "--challenge", "Baby ROP", "--category", "pwn"]
    )

    assert result.exit_code == 0
    assert (challenge.path / "solve.py").read_text() == "MY EXPLOIT"
    assert "--force" in result.output


def test_scaffold_force_overwrites():
    ctf = _ctf("ScaffoldCTF")
    challenge = _challenge(ctf, "Baby ROP")
    _install_plugin(Category.pwn, "pwnplug", "PWN")
    challenge.path.mkdir(parents=True, exist_ok=True)
    (challenge.path / "solve.py").write_text("MY EXPLOIT", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "challenge",
            "scaffold",
            "--challenge",
            "Baby ROP",
            "--category",
            "pwn",
            "--force",
        ],
    )

    assert result.exit_code == 0
    assert (challenge.path / "solve.py").read_text() == "# PWN Baby ROP\n"


def test_scaffold_applies_a_foreign_category_without_touching_the_challenge():
    ctf = _ctf("ScaffoldCTF")
    challenge = _challenge(ctf, "EZ XSS", category=Category.web)
    _install_plugin(Category.pwn, "pwnplug", "PWN")
    _install_plugin(Category.web, "webplug", "WEB")

    CliRunner().invoke(
        app, ["challenge", "scaffold", "--challenge", "EZ XSS", "--category", "web"]
    )
    result = CliRunner().invoke(
        app,
        [
            "challenge",
            "scaffold",
            "--challenge",
            "EZ XSS",
            "--category",
            "pwn",
            "--suffix",
            "_pwn",
        ],
    )

    assert result.exit_code == 0
    assert (challenge.path / "solve.py").read_text() == "# WEB EZ XSS\n"
    assert (challenge.path / "solve_pwn.py").read_text() == "# PWN EZ XSS\n"

    stored = next(ch for ch in get_challenges() if ch.name == "EZ XSS")
    assert stored.category == Category.web
    assert stored.path == challenge.path


def test_scaffold_reports_a_category_with_no_plugin():
    ctf = _ctf("ScaffoldCTF")
    _challenge(ctf, "Baby ROP")

    result = CliRunner().invoke(
        app,
        ["challenge", "scaffold", "--challenge", "Baby ROP", "--category", "crypto"],
    )

    assert result.exit_code == 1
    assert "plugin select" in result.output


def test_challenge_path_prints_only_the_directory():
    ctf = _ctf("PathCTF")
    challenge = _challenge(ctf, "Baby ROP")

    result = _runner().invoke(app, ["challenge", "path", "Baby ROP"])

    assert result.exit_code == 0
    assert result.stdout.strip() == str(challenge.path)


def test_challenge_path_accepts_the_directory_name():
    ctf = _ctf("PathCTF")
    challenge = _challenge(ctf, "Baby ROP")

    result = _runner().invoke(app, ["challenge", "path", "baby-rop"])

    assert result.exit_code == 0
    assert result.stdout.strip() == str(challenge.path)


def test_duplicate_names_resolve_to_the_running_ctf():
    live = _ctf("LiveCTF")
    old = _ctf("OldCTF", running=Status.stopped)
    wanted = _challenge(live, "Sanity")
    _challenge(old, "Sanity")

    result = _runner().invoke(app, ["challenge", "path", "Sanity"])

    assert result.exit_code == 0
    assert result.stdout.strip() == str(wanted.path)


def test_ambiguous_names_across_running_ctfs_reach_the_picker(monkeypatch):
    first = _ctf("FirstCTF")
    second = _ctf("SecondCTF")
    _challenge(first, "Sanity")
    chosen = _challenge(second, "Sanity")

    offered = {}

    def _pick(challenges, msg):
        offered["names"] = [ch.name for ch in challenges]
        offered["message"] = msg
        return chosen

    monkeypatch.setattr("pwnv.utils.ui.prompt_challenge_selection", _pick)

    result = _runner().invoke(app, ["challenge", "path", "Sanity"])

    assert result.exit_code == 0
    assert result.stdout.strip() == str(chosen.path)
    assert offered["names"] == ["Sanity", "Sanity"]
    assert "Sanity" in offered["message"]


def test_challenge_path_fails_loudly_on_a_miss():
    ctf = _ctf("PathCTF")
    _challenge(ctf, "Baby ROP")

    result = _runner().invoke(app, ["challenge", "path", "nope"])

    assert result.exit_code == 1
    assert result.stdout.strip() == ""
    assert "does not exist" in result.stderr


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_shell_init_emits_a_pwncd_function(shell):
    result = CliRunner().invoke(app, ["shell-init", "--shell", shell])

    assert result.exit_code == 0
    assert "pwncd" in result.output
    assert "pwnv challenge path" in result.output


def test_shell_init_rejects_an_unknown_shell():
    result = CliRunner().invoke(app, ["shell-init", "--shell", "nushell"])

    assert result.exit_code == 1


class _Attachment:
    def __init__(self, name: str, payload: bytes):
        self.name = name
        self.payload = payload
        self.size_bytes = len(payload)
        self.local_path: str | None = None

    def model_dump(self, mode: str = "json") -> dict:
        return {
            "name": self.name,
            "size_bytes": self.size_bytes,
            "local_path": self.local_path,
        }


class _FakeAttachments:
    def __init__(self):
        self.downloaded: list[str] = []

    async def download_all(self, ch, save_dir):
        self.downloaded.append(ch.name)
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        for attachment in ch.attachments:
            target = Path(save_dir) / attachment.name
            target.write_bytes(attachment.payload)
            attachment.local_path = str(target)
        return ch


def _fake_client():
    attachments = _FakeAttachments()
    return SimpleNamespace(attachments=attachments), attachments


def _remote(
    name, *, value=100, solved=False, description="", attachments=None, tags=None
):
    return SimpleNamespace(
        id=f"remote-{name}",
        name=name,
        category="pwn",
        value=value,
        solved=solved,
        description=description,
        author="admin",
        tags=tags or [],
        attachments=attachments or [],
        services=[],
    )


def _sync(client, ctf, challenges, **kwargs):
    from pwnv.utils.remote import add_remote_challenges

    return asyncio.run(
        add_remote_challenges(client, ctf, challenges, report=False, **kwargs)
    )


def test_unchanged_attachments_are_not_downloaded_twice():
    ctf = _ctf("AttachCTF", url="https://x.invalid")
    client, attachments = _fake_client()
    payload = [_remote("Baby ROP", attachments=[_Attachment("chal.zip", b"binary")])]

    first = _sync(client, ctf, payload)
    assert attachments.downloaded == ["Baby ROP"]
    assert first["attachments_downloaded"] == ["Baby ROP"]

    second = _sync(
        client,
        ctf,
        [_remote("Baby ROP", attachments=[_Attachment("chal.zip", b"binary")])],
    )

    assert attachments.downloaded == ["Baby ROP"]
    assert second["attachments_reused"] == ["Baby ROP"]
    assert second["unchanged"] == 1


def test_a_republished_attachment_is_downloaded_again():
    ctf = _ctf("AttachCTF", url="https://x.invalid")
    client, attachments = _fake_client()
    _sync(
        client, ctf, [_remote("Baby ROP", attachments=[_Attachment("chal.zip", b"v1")])]
    )

    stored = get_challenges()[0]
    Path(stored.extras["attachments"][0]["local_path"]).write_bytes(b"tampered")

    _sync(
        client, ctf, [_remote("Baby ROP", attachments=[_Attachment("chal.zip", b"v2")])]
    )

    assert attachments.downloaded == ["Baby ROP", "Baby ROP"]


def test_a_deleted_attachment_is_downloaded_again():
    ctf = _ctf("AttachCTF", url="https://x.invalid")
    client, attachments = _fake_client()
    _sync(
        client, ctf, [_remote("Baby ROP", attachments=[_Attachment("chal.zip", b"v1")])]
    )

    Path(get_challenges()[0].extras["attachments"][0]["local_path"]).unlink()

    _sync(
        client, ctf, [_remote("Baby ROP", attachments=[_Attachment("chal.zip", b"v1")])]
    )

    assert attachments.downloaded == ["Baby ROP", "Baby ROP"]


def test_refresh_attachments_forces_a_download():
    ctf = _ctf("AttachCTF", url="https://x.invalid")
    client, attachments = _fake_client()
    _sync(
        client, ctf, [_remote("Baby ROP", attachments=[_Attachment("chal.zip", b"v1")])]
    )

    _sync(
        client,
        ctf,
        [_remote("Baby ROP", attachments=[_Attachment("chal.zip", b"v1")])],
        refresh_attachments=True,
    )

    assert attachments.downloaded == ["Baby ROP", "Baby ROP"]


def test_sync_summarises_what_actually_changed():
    ctf = _ctf("DiffCTF", url="https://x.invalid")
    client, _ = _fake_client()
    _sync(client, ctf, [_remote("Baby ROP", value=100), _remote("Sanity", value=10)])

    summary = _sync(
        client,
        ctf,
        [
            _remote("Baby ROP", value=80, solved=True),
            _remote("Sanity", value=10),
            _remote("New Chal", value=500),
        ],
    )

    assert summary["added"] == ["New Chal"]
    assert summary["unchanged"] == 1
    changed = {item["name"]: item["changes"] for item in summary["updated"]}
    assert "100 -> 80 pts" in changed["Baby ROP"]
    assert "solved on platform" in changed["Baby ROP"]


def test_sync_notices_an_edited_description():
    ctf = _ctf("DiffCTF", url="https://x.invalid")
    client, _ = _fake_client()
    _sync(client, ctf, [_remote("Baby ROP", description="original")])

    summary = _sync(client, ctf, [_remote("Baby ROP", description="now with a hint")])

    assert summary["updated"][0]["changes"] == ["description changed"]


def test_watch_stops_when_the_ctf_stops(monkeypatch):
    import time

    import pwnv.utils as utils

    _ctf("WatchCTF", url="https://x.invalid")
    polls = []

    def _fake_sync(selected, **kwargs):
        polls.append(selected.name)
        selected.running = Status.stopped
        utils.update_ctf(selected)
        return {"added": [], "updated": [], "unchanged": 0}

    monkeypatch.setattr(utils, "sync_remote_ctf", _fake_sync)
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)

    result = CliRunner().invoke(
        app, ["ctf", "sync", "--ctf", "WatchCTF", "--watch", "--interval", "10"]
    )

    assert result.exit_code == 0
    assert polls == ["WatchCTF"]
    assert "no longer running" in result.output


def test_sync_renders_a_diff_instead_of_the_whole_scoreboard(monkeypatch):
    import pwnv.utils as utils

    _ctf("DiffCTF", url="https://x.invalid")

    monkeypatch.setattr(
        utils,
        "sync_remote_ctf",
        lambda selected, **kwargs: {
            "added": ["New Chal"],
            "updated": [{"name": "Baby ROP", "changes": ["100 -> 80 pts"]}],
            "unchanged": 12,
            "attachments_downloaded": ["New Chal"],
            "attachments_reused": [],
        },
    )

    result = CliRunner().invoke(app, ["ctf", "sync", "--ctf", "DiffCTF"])

    assert result.exit_code == 0
    assert "New Chal" in result.output
    assert "100 -> 80 pts" in result.output
    assert "12 unchanged" in result.output


def test_status_detail_breaks_a_ctf_down_by_category():
    ctf = _ctf("StatusCTF", url="https://x.invalid")
    _challenge(
        ctf,
        "Sanity",
        category=Category.misc,
        points=10,
        solved=Solved.solved,
        extras={
            "flag_history": [{"timestamp": "2026-09-01T12:00:00", "result": "accepted"}]
        },
    )
    _challenge(
        ctf,
        "Baby ROP",
        points=100,
        extras={"services": [{"host": "chal.invalid", "port": 1337}]},
    )

    result = CliRunner().invoke(app, ["status", "--ctf", "StatusCTF", "--detail"])

    assert result.exit_code == 0
    assert "by category" in result.output
    assert "Recent solves" in result.output
    assert "Next up" in result.output
    assert "nc chal.invalid 1337" in result.output


def test_status_json_carries_the_detail_and_current_scope():
    ctf = _ctf("StatusCTF")
    _challenge(ctf, "Baby ROP", points=100)

    result = CliRunner().invoke(
        app, ["status", "--ctf", "StatusCTF", "--detail", "--json"]
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ctfs"][0]["ctf"] == "StatusCTF"
    assert payload["ctfs"][0]["remote"] is False
    assert payload["detail"]["next_up"][0]["name"] == "Baby ROP"
    assert payload["current"]["ctf"] == "StatusCTF"


def _run_init(isolated_config, tmp_path, monkeypatch, *extra: str):
    isolated_config.unlink()
    monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/uv")
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **kw: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    return CliRunner().invoke(
        app,
        [
            "init",
            "--yes",
            "--no-install",
            "--ctfs-folder",
            str(tmp_path / "CTF"),
            *extra,
        ],
    )


def test_init_copies_the_bundled_plugins_and_templates(
    isolated_config, tmp_path, monkeypatch
):
    from pwnv.utils import (
        get_plugin_selection,
        get_plugins_directory,
        get_templates_directory,
    )

    result = _run_init(isolated_config, tmp_path, monkeypatch)

    assert result.exit_code == 0
    assert (get_plugins_directory() / "pwn_example.py").is_file()
    assert (get_templates_directory() / "pwn" / "rop.py").is_file()
    assert get_plugin_selection()["pwn"] == "pwn_example"


def test_init_can_skip_the_bundled_examples(isolated_config, tmp_path, monkeypatch):
    from pwnv.utils import get_plugin_selection, get_plugins_directory

    result = _run_init(isolated_config, tmp_path, monkeypatch, "--no-examples")

    assert result.exit_code == 0
    assert not (get_plugins_directory() / "pwn_example.py").exists()
    assert get_plugin_selection() == {}


def test_bundled_examples_never_overwrite_your_edits():
    from pwnv.utils import (
        get_plugin_selection,
        get_plugins_directory,
        install_bundled_examples,
        set_selected_plugin_for_category,
    )

    install_bundled_examples()
    mine = get_plugins_directory() / "pwn_example.py"
    mine.write_text("# my version\n", encoding="utf-8")
    set_selected_plugin_for_category(Category.pwn, "something_else")

    installed = install_bundled_examples()

    assert installed == []
    assert mine.read_text() == "# my version\n"
    assert get_plugin_selection()["pwn"] == "something_else"


def test_the_bundled_plugin_actually_loads():
    from pwnv.core.plugin_manager import plugin_manager
    from pwnv.utils import install_bundled_examples

    install_bundled_examples()
    plugin_manager._loaded = False  # type: ignore[attr-defined]
    plugin_manager.get_all_plugins.cache_clear()  # type: ignore[attr-defined]

    plugin = plugin_manager.get_plugin_by_name("pwn_example")

    assert plugin is not None
    assert plugin.category() == Category.pwn
