from types import SimpleNamespace

from typer.testing import CliRunner

from pwnv import app
from pwnv.models import CTF, Challenge
from pwnv.models.challenge import Category, Solved
from pwnv.utils import add_challenge, add_ctf, get_challenges, get_ctfs_path


def _workspace():
    ctf = CTF(name="ExampleCTF", path=get_ctfs_path() / "example-ctf")
    add_ctf(ctf)
    first = Challenge(
        name="First Blood",
        ctf_id=ctf.id,
        path=ctf.path / "pwn" / "first-blood",
        category=Category.pwn,
        points=100,
        tags=["rop"],
        extras={
            "description": "A stack overflow",
            "services": [{"host": "example.com", "port": 31337}],
        },
    )
    second = Challenge(
        name="Cipher",
        ctf_id=ctf.id,
        path=ctf.path / "crypto" / "cipher",
        category=Category.crypto,
        points=50,
        solved=Solved.solved,
    )
    add_challenge(first)
    add_challenge(second)
    return ctf, first, second


def test_explicit_ctf_sync_skips_selector(monkeypatch):
    import pwnv.utils as utils

    ctf, _, _ = _workspace()
    ctf.url = "https://example.invalid"
    utils.update_ctf(ctf)
    synced = []

    def _sync(selected):
        synced.append(selected)
        return True

    monkeypatch.setattr(utils, "sync_remote_ctf", _sync)

    result = CliRunner().invoke(app, ["ctf", "sync", "--ctf", "ExampleCTF"])

    assert result.exit_code == 0
    assert synced[0].id == ctf.id


def test_doctor_and_status_commands():
    _workspace()
    runner = CliRunner()

    doctor = runner.invoke(app, ["doctor"])
    status = runner.invoke(app, ["status", "--ctf", "ExampleCTF"])

    assert doctor.exit_code == 0
    assert "0 failed" in doctor.output
    assert status.exit_code == 0
    assert "1/2" in status.output
    assert "50/150" in status.output


def test_notes_are_written_and_rendered():
    _, first, _ = _workspace()
    runner = CliRunner()

    added = runner.invoke(
        app,
        [
            "challenge",
            "note",
            "add",
            "Offset is 72 bytes",
            "--section",
            "Pwn",
            "--challenge",
            "First Blood",
            "--ctf",
            "ExampleCTF",
        ],
    )
    shown = runner.invoke(
        app,
        [
            "challenge",
            "note",
            "show",
            "--challenge",
            "First Blood",
            "--ctf",
            "ExampleCTF",
        ],
    )

    assert added.exit_code == 0
    assert "Offset is 72 bytes" in first.path.joinpath("NOTES.md").read_text()
    assert shown.exit_code == 0
    assert "Offset is 72 bytes" in shown.output


def test_structured_search_filters_results():
    _workspace()
    result = CliRunner().invoke(
        app,
        [
            "challenge",
            "search",
            "--ctf",
            "ExampleCTF",
            "--category",
            "pwn",
            "--tag",
            "rop",
            "--min-points",
            "75",
            "--has-service",
            "--unsolved",
        ],
    )

    assert result.exit_code == 0
    assert "First Blood" in result.output
    assert "Cipher" not in result.output


def test_challenge_environment_add_uses_local_venv(monkeypatch):
    _, first, _ = _workspace()
    calls = []

    def _run(command, **kwargs):
        calls.append(command)
        if command[:2] == ["uv", "venv"]:
            python = first.path / ".venv" / "bin" / "python"
            python.parent.mkdir(parents=True, exist_ok=True)
            python.touch()
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("subprocess.run", _run)
    result = CliRunner().invoke(
        app,
        [
            "challenge",
            "env",
            "add",
            "pwntools",
            "--challenge",
            "First Blood",
            "--ctf",
            "ExampleCTF",
        ],
    )

    assert result.exit_code == 0
    assert calls[0][:2] == ["uv", "venv"]
    assert calls[1][:3] == ["uv", "pip", "install"]
    assert calls[1][-1] == "pwntools"


def test_solve_records_and_redacts_flag_history():
    _workspace()
    runner = CliRunner()
    solved = runner.invoke(
        app,
        [
            "solve",
            "--flag",
            "FLAG{secret}",
            "--challenge",
            "First Blood",
            "--ctf",
            "ExampleCTF",
            "--tags",
            "",
        ],
    )
    history = runner.invoke(
        app,
        [
            "solve",
            "--history",
            "--challenge",
            "First Blood",
            "--ctf",
            "ExampleCTF",
        ],
    )

    assert solved.exit_code == 0
    attempts = get_challenges()[0].extras["flag_history"]
    assert attempts[0]["flag"] == "FLAG{secret}"
    assert attempts[0]["result"] == "local"
    assert history.exit_code == 0
    assert "FLAG{secret}" not in history.output
    assert "••••••••" in history.output
