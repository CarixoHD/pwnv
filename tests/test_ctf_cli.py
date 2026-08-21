from typer.testing import CliRunner

from pwnv import app


def test_add_remote_ctf_noninteractive_credentials(monkeypatch):
    import pwnv.utils as utils

    captured = {}

    def _add_remote(ctf, credentials):
        captured["ctf"] = ctf
        captured["credentials"] = credentials
        return True

    monkeypatch.setattr(utils, "add_remote_ctf", _add_remote)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "ctf",
            "add",
            "Demo",
            "--url",
            "https://demo.ctfd.io/",
            "--username",
            "user",
            "--password",
            "password",
        ],
    )

    assert result.exit_code == 0
    assert captured["ctf"].url == "https://demo.ctfd.io/"
    assert captured["credentials"] == {
        "username": "user",
        "password": "password",
        "token": None,
    }


def test_add_remote_ctf_rejects_partial_credentials():
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["ctf", "add", "Demo", "--url", "https://demo.ctfd.io/", "--username", "user"],
    )

    assert result.exit_code == 1
    assert "must be provided together" in result.output
