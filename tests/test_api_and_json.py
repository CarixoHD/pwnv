"""Tests for the solve-script object and the machine-readable output contract."""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pwnv.models import CTF, Challenge
from pwnv.models.challenge import Category, Solved
from pwnv.models.ctf import Status
from pwnv.utils import add_challenge, add_ctf, get_ctfs_path

# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #


def _ctf(name: str, *, running: Status = Status.running, url: str | None = None) -> CTF:
    ctf = CTF(name=name, path=get_ctfs_path() / name.lower(), running=running, url=url)
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


def _service(host: str = "chal.example.org", port: int = 1337) -> dict:
    return {"host": host, "port": port, "type": "tcp", "raw": f"nc {host} {port}"}


def _stored_challenges():
    from pwnv.utils import get_challenges

    return get_challenges()


def _update(challenge) -> None:
    from pwnv.utils import update_challenge

    update_challenge(challenge)


def _strict_runner() -> CliRunner:
    """A runner that keeps stderr out of stdout, so `--json` can be parsed."""
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:  # click >= 8.2 never mixes them
        return CliRunner()


def _invoke(*args: str):
    from pwnv import app

    return _strict_runner().invoke(app, list(args))


# --------------------------------------------------------------------------- #
# resolution
# --------------------------------------------------------------------------- #


def test_it_resolves_the_challenge_you_are_standing_in(monkeypatch):
    from pwnv.api import current

    ctf = _ctf("ApiCTF")
    challenge = _challenge(ctf, "Baby ROP", points=250, tags=["rop"])
    monkeypatch.chdir(challenge.path)

    resolved = current()
    assert resolved.name == "Baby ROP"
    assert resolved.category == "pwn"
    assert resolved.value == 250
    assert resolved.tags == ["rop"]
    assert resolved.path == challenge.path


def test_a_subdirectory_still_resolves_to_the_challenge(monkeypatch):
    from pwnv.api import current

    ctf = _ctf("ApiCTF")
    challenge = _challenge(ctf, "Nested")
    nested = challenge.path / "src" / "deep"
    nested.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(nested)

    assert current().name == "Nested"


def test_outside_a_challenge_it_says_where_it_looked(monkeypatch, tmp_path):
    from pwnv.api import NoChallengeError, current

    elsewhere = tmp_path / "not-a-challenge"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    with pytest.raises(NoChallengeError, match=str(elsewhere)):
        current()


def test_a_path_can_be_asked_about_directly(monkeypatch, tmp_path):
    from pwnv.api import current

    ctf = _ctf("ApiCTF")
    challenge = _challenge(ctf, "Elsewhere")
    monkeypatch.chdir(tmp_path)

    assert current(challenge.path).name == "Elsewhere"


def test_it_sees_a_sync_that_ran_after_the_script_started(monkeypatch):
    """The whole point: values bind when they are read, not when scaffolded."""
    from pwnv.api import current
    from pwnv.utils import get_challenges, update_challenge

    ctf = _ctf("ApiCTF")
    challenge = _challenge(ctf, "Moving Target", extras={"services": [_service()]})
    monkeypatch.chdir(challenge.path)
    assert current().service.host == "chal.example.org"

    stored = next(item for item in get_challenges() if item.name == "Moving Target")
    stored.extras = {"services": [_service("relocated.example.org", 31337)]}
    update_challenge(stored)

    moved = current().service
    assert (moved.host, moved.port) == ("relocated.example.org", 31337)


# --------------------------------------------------------------------------- #
# it is a ctfbridge challenge
# --------------------------------------------------------------------------- #


def test_what_comes_back_is_the_platform_model(monkeypatch):
    """No pwnv wrapper: the helpers a solve script uses are ctfbridge's own."""
    from ctfbridge.models.challenge import Challenge as BridgeChallenge

    from pwnv.api import current

    ctf = _ctf("ApiCTF")
    challenge = _challenge(
        ctf,
        "Baby ROP",
        extras={
            "services": [_service()],
            "description": "smash it",
            "author": "organiser",
            "slug": "baby-rop",
        },
    )
    monkeypatch.chdir(challenge.path)

    resolved = current()
    assert isinstance(resolved, BridgeChallenge)
    assert resolved.id == "baby-rop"
    assert resolved.description == "smash it"
    assert resolved.author == "organiser"
    assert resolved.has_services is True
    assert resolved.service.host == "chal.example.org"
    assert resolved.service.port == 1337
    assert resolved.service.raw == "nc chal.example.org 1337"


def test_a_local_challenge_has_no_service(monkeypatch):
    from pwnv.api import current

    ctf = _ctf("LocalCTF", url=None)
    challenge = _challenge(ctf, "Offline")
    monkeypatch.chdir(challenge.path)

    resolved = current()
    assert resolved.services == []
    assert resolved.service is None
    assert resolved.has_services is False


def test_attachments_arrive_as_the_collection_with_their_local_paths(monkeypatch):
    from pwnv.api import current

    ctf = _ctf("ApiCTF")
    challenge = _challenge(ctf, "Handout")
    challenge.path.mkdir(parents=True, exist_ok=True)
    binary = challenge.path / "vuln"
    binary.write_bytes(b"\x7fELF")

    stored = next(item for item in _stored_challenges() if item.name == "Handout")
    stored.extras = {
        "attachments": [
            # `sha256` is pwnv's own bookkeeping; the platform model ignores it.
            {"name": "vuln", "local_path": str(binary), "sha256": "deadbeef"}
        ]
    }
    _update(stored)
    monkeypatch.chdir(challenge.path)

    attachments = current().attachments
    assert len(attachments) == 1
    assert attachments[0].name == "vuln"
    assert Path(attachments[0].local_path) == binary


def test_solved_and_flag_come_from_the_local_record(monkeypatch):
    from pwnv.api import current

    ctf = _ctf("ApiCTF")
    challenge = _challenge(ctf, "Done", solved=Solved.solved, flag="flag{x}")
    monkeypatch.chdir(challenge.path)

    resolved = current()
    assert resolved.solved is True
    assert resolved.flag == "flag{x}"


# --------------------------------------------------------------------------- #
# import cost
# --------------------------------------------------------------------------- #


def test_importing_the_object_does_not_drag_in_the_cli(monkeypatch):
    """
    A solve script pays for what it uses.

    Assembling the Typer app imports every command module; resolving a challenge
    needs none of them, so `from pwnv import challenge` must not reach typer.
    """
    ctf = _ctf("ApiCTF")
    challenge = _challenge(ctf, "Probe")

    probe = textwrap.dedent(
        """
        import sys

        from pwnv import challenge

        assert "typer" not in sys.modules, sorted(
            name for name in sys.modules if name.startswith("typer")
        )
        print(challenge.name)
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        cwd=challenge.path,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "Probe"


def test_the_default_config_location_does_not_reach_for_typer(tmp_path):
    """
    The same assertion, on the branch an ordinary install actually takes.

    With no `PWNV_CONFIG` and no config file above the working directory, the
    path comes from the application directory - which used to be resolved with
    `typer.get_app_dir`, so every solve script on a normal machine imported the
    CLI after all. It is `click.get_app_dir`, which typer only re-exports.
    """
    home = tmp_path / "home"
    (home / ".config").mkdir(parents=True)
    work = tmp_path / "work"
    work.mkdir()

    env = {
        **os.environ,
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
    }
    env.pop("PWNV_CONFIG", None)

    probe = textwrap.dedent(
        """
        import sys
        from pathlib import Path

        from pwnv.utils.config import config_path

        assert "typer" not in sys.modules, sorted(
            name for name in sys.modules if name.startswith("typer")
        )

        import click

        assert config_path == Path(click.get_app_dir("pwnv")) / "pwnv_config.json"
        print(config_path)
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        cwd=work,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().startswith(str(home))


# --------------------------------------------------------------------------- #
# the json contract
# --------------------------------------------------------------------------- #


def test_challenge_info_json_carries_the_whole_record(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    ctf = _ctf("JsonCTF")
    _challenge(
        ctf,
        "Baby ROP",
        points=250,
        tags=["rop"],
        solved=Solved.solved,
        flag="flag{ok}",
        extras={"services": [_service()], "description": "smash it", "author": "me"},
    )

    result = _invoke("challenge", "info", "--challenge", "Baby ROP", "--json")

    assert result.exit_code == 0
    (payload,) = json.loads(result.stdout)["challenges"]
    assert payload["name"] == "Baby ROP"
    assert payload["ctf"] == "JsonCTF"
    assert payload["category"] == "pwn"
    assert payload["points"] == 250
    assert payload["solved"] is True
    assert payload["tags"] == ["rop"]
    assert payload["services"][0]["host"] == "chal.example.org"
    assert payload["description"] == "smash it"


def test_json_mode_reports_the_scope_instead_of_opening_a_picker(monkeypatch, tmp_path):
    """There is nobody to answer a prompt on the other end of a pipe."""
    monkeypatch.chdir(tmp_path)
    ctf = _ctf("JsonCTF")
    _challenge(ctf, "One")
    _challenge(ctf, "Two")
    other = _ctf("OtherCTF")
    _challenge(other, "Three")

    result = _invoke("challenge", "info", "--json")

    assert result.exit_code == 0
    names = {item["name"] for item in json.loads(result.stdout)["challenges"]}
    assert names == {"One", "Two", "Three"}


def test_json_mode_prefers_the_challenge_you_are_standing_in(monkeypatch):
    ctf = _ctf("JsonCTF")
    _challenge(ctf, "One")
    here = _challenge(ctf, "Two")
    monkeypatch.chdir(here.path)

    result = _invoke("challenge", "info", "--json")

    assert result.exit_code == 0
    names = [item["name"] for item in json.loads(result.stdout)["challenges"]]
    assert names == ["Two"]


def test_ctf_scoped_json_ignores_the_directory_you_happen_to_be_in(monkeypatch):
    ctf = _ctf("JsonCTF")
    here = _challenge(ctf, "One")
    _challenge(ctf, "Two")
    monkeypatch.chdir(here.path)

    result = _invoke("challenge", "info", "--ctf", "JsonCTF", "--json")

    assert result.exit_code == 0
    names = {item["name"] for item in json.loads(result.stdout)["challenges"]}
    assert names == {"One", "Two"}


def test_search_json_returns_an_empty_list_rather_than_a_warning(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    ctf = _ctf("JsonCTF")
    _challenge(ctf, "Baby ROP")

    result = _invoke("challenge", "search", "nothing-matches-this", "--json")

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"challenges": []}


def test_ctf_info_json_counts_challenges_and_solves(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    ctf = _ctf("JsonCTF", url="https://example.org")
    _challenge(ctf, "One", solved=Solved.solved)
    _challenge(ctf, "Two")

    result = _invoke("ctf", "info", "--ctf", "JsonCTF", "--json")

    assert result.exit_code == 0
    (payload,) = json.loads(result.stdout)["ctfs"]
    assert payload["name"] == "JsonCTF"
    assert payload["url"] == "https://example.org"
    assert payload["running"] is True
    assert payload["challenges"] == 2
    assert payload["solved"] == 1


def test_ctf_info_json_without_a_name_lists_every_ctf(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _ctf("First")
    _ctf("Second")

    result = _invoke("ctf", "info", "--json")

    assert result.exit_code == 0
    assert {item["name"] for item in json.loads(result.stdout)["ctfs"]} == {
        "First",
        "Second",
    }


def test_plugin_info_json_reports_selection_without_the_source(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    from tests.test_workflow_features import _install_plugin

    _install_plugin(Category.pwn, "pwnplug", "PWN")

    result = _invoke("plugin", "info", "--json")

    assert result.exit_code == 0
    (payload,) = json.loads(result.stdout)["plugins"]
    assert payload["name"] == "pwnplug"
    assert payload["category"] == "pwn"
    assert payload["selected"] is True
    assert payload["file"].endswith("pwnplug.py")


def test_status_json_still_parses_now_that_it_shares_the_flag(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    ctf = _ctf("JsonCTF")
    _challenge(ctf, "One", points=100, solved=Solved.solved)

    result = _invoke("status", "--json")

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ctfs"][0]["ctf"] == "JsonCTF"


# --------------------------------------------------------------------------- #
# stdout stays a data channel
# --------------------------------------------------------------------------- #


def test_diagnostics_never_land_in_the_data_channel(monkeypatch, tmp_path):
    """
    A warning printed on stdout would make `--json` output impossible to parse.

    `challenge info --json` for a missing CTF must put the complaint on stderr
    and nothing at all on stdout.
    """
    monkeypatch.chdir(tmp_path)
    ctf = _ctf("JsonCTF")
    _challenge(ctf, "One")

    result = _invoke("challenge", "info", "--ctf", "Nope", "--json")

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "does not exist" in result.stderr


def test_the_no_challenges_guard_writes_to_stderr(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    result = _invoke("challenge", "info")

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "No challenges found" in result.stderr


@pytest.mark.parametrize(
    "argv, key",
    [
        (["challenge", "info", "--json"], "challenges"),
        (["challenge", "search", "--json"], "challenges"),
        (["ctf", "info", "--json"], "ctfs"),
        (["plugin", "info", "--json"], "plugins"),
    ],
)
def test_an_empty_workspace_is_an_empty_list_not_an_error(
    monkeypatch, tmp_path, argv, key
):
    """
    The guards that check for records must not fire in `--json` mode.

    "There is nothing here" is an answer a script can act on; exit code 1 with
    no document at all is one it has to tell apart from a crash.
    """
    monkeypatch.chdir(tmp_path)

    result = _invoke(*argv)

    assert result.exit_code == 0, result.stderr
    assert json.loads(result.stdout) == {key: []}
