import os
import shutil

import pytest

from pwnv.models import CTF
from pwnv.utils import add_remote_ctf, get_ctfs_path, sanitize


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Basic Challenge", "basic-challenge"),
        ("../Escape\\Attempt", "_escape_attempt"),
        ("...", "challenge"),
        ("line\nbreak", "line-break"),
    ],
)
def test_sanitize_produces_safe_challenge_names(name, expected):
    assert sanitize(name) == expected


@pytest.mark.skipif(
    os.getenv("ENABLE_REMOTE_CTFS", "0") != "1",
    reason=(
        "Remote integration tests are opt-in. "
        "Set ENABLE_REMOTE_CTFS=1 to run against demo.ctfd.io."
    ),
)
def test_add_remote_ctf_integration(monkeypatch, isolated_config):
    """
    Minimal integration test against the public demo CTFd instance.

    The test is opt-in via ENABLE_REMOTE_CTFS=1 and runs entirely in the
    isolated config/ctfs path provided by the tests fixture.
    """
    url = "https://demo.ctfd.io/"
    username = os.getenv("DEMO_CTFD_USER", "user")
    password = os.getenv("DEMO_CTFD_PASS", "password")

    # Force deterministic, non-interactive credential prompts.
    def _dummy_prompt(value):
        class _P:
            def execute(self_nonlocal):
                return value

        return _P()

    def _select(**kwargs):
        choices = kwargs.get("choices") or []
        value = choices[0]["value"] if choices else None
        return _dummy_prompt(value)

    def _secret(**kwargs):
        return _dummy_prompt(password)

    def _text(**kwargs):
        return _dummy_prompt(username)

    from InquirerPy import inquirer as _inq

    import pwnv.utils.remote as remote

    monkeypatch.setattr(_inq, "select", _select)
    monkeypatch.setattr(_inq, "secret", _secret)
    monkeypatch.setattr(_inq, "text", _text)
    monkeypatch.setattr(
        remote,
        "_ask_for_credentials",
        lambda methods: {"username": username, "password": password, "token": None},
    )

    ctfs_path = get_ctfs_path()
    ctf_path = ctfs_path / "demo-ctfd"
    ctf = CTF(name="DemoCTFd", path=ctf_path, url=url)

    # Clean slate
    if ctf_path.exists():
        shutil.rmtree(ctf_path)
    ctf_path.mkdir(parents=True, exist_ok=True)

    # Pre-seed .env to bypass prompt
    (ctf_path / ".env").write_text(
        f"CTF_USERNAME={username}\nCTF_PASSWORD={password}\n", encoding="utf-8"
    )

    added = add_remote_ctf(ctf)
    assert added, "Failed to add remote CTF"

    assert ctf_path.exists() and ctf_path.is_dir()
    assert any(ctf_path.iterdir()), "Expected remote sync to create challenge data"


def test_add_remote_ctf_fails_when_client_unavailable(monkeypatch, isolated_config):
    import pwnv.utils.remote as remote

    ctfs_path = get_ctfs_path()
    ctf_path = ctfs_path / "failing-ctf"
    ctf = CTF(name="FailingCTF", path=ctf_path, url="https://example.invalid")

    # Simulate inability to create a client/auth methods (network or URL failure)

    async def _no_client(url):
        return None, None

    monkeypatch.setattr(remote, "get_remote_credential_methods", _no_client)

    added = add_remote_ctf(ctf)
    assert added is False
    assert not ctf_path.exists()


def test_add_remote_ctf_fails_when_credentials_missing(monkeypatch, isolated_config):
    import pwnv.utils.remote as remote

    ctfs_path = get_ctfs_path()
    ctf_path = ctfs_path / "nocreds"
    ctf = CTF(name="NoCreds", path=ctf_path, url="https://demo.ctfd.io/")

    # Simulate available methods but user supplies no credentials

    async def _fake_methods(url):
        return "dummy_client", ["creds"]

    monkeypatch.setattr(remote, "get_remote_credential_methods", _fake_methods)
    monkeypatch.setattr(remote, "_ask_for_credentials", lambda methods: {})

    added = add_remote_ctf(ctf)
    assert added is False
    assert not ctf_path.exists()
