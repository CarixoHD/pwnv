import os
import shutil
from types import SimpleNamespace

import pytest

from pwnv.models import CTF, Challenge
from pwnv.models.challenge import Category, Solved
from pwnv.utils import (
    add_challenge,
    add_ctf,
    add_remote_ctf,
    get_challenges,
    get_ctfs_path,
    sanitize,
    sync_remote_ctf,
)


class _RemoteMetadata:
    def __init__(self, **values):
        self.values = values

    def model_dump(self, mode="json"):
        return self.values


class _Attachments:
    async def download_all(self, challenge, save_dir):
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "updated.txt").write_text("attachment", encoding="utf-8")
        return challenge


def test_remote_sync_updates_existing_challenge_metadata(tmp_path):
    import pwnv.utils.remote as remote

    ctf = CTF(name="Remote", path=get_ctfs_path() / "remote", url="https://ctf")
    add_ctf(ctf)
    existing = Challenge(
        name="old-name",
        ctf_id=ctf.id,
        path=ctf.path / "pwn" / "old-name",
        points=50,
        solved=Solved.solved,
        tags=["local"],
        extras={"slug": 42, "description": "old"},
    )
    add_challenge(existing)
    fetched = SimpleNamespace(
        id=42,
        name="Renamed Challenge",
        category="web",
        value=200,
        solved=False,
        description="new searchable description",
        attachments=[_RemoteMetadata(name="updated.txt")],
        services=[_RemoteMetadata(host="example.com", port=443)],
        author="author",
        tags=["remote"],
    )
    client = SimpleNamespace(attachments=_Attachments())

    remote._run_async(remote.add_remote_challenges(client, ctf, [fetched]))

    updated = get_challenges()[0]
    assert updated.points == 200
    assert updated.category == Category.web
    assert updated.solved == Solved.solved
    assert updated.tags == ["local", "remote"]
    assert updated.extras["description"] == "new searchable description"
    assert updated.extras["services"] == [{"host": "example.com", "port": 443}]
    assert (updated.path / "updated.txt").read_text(encoding="utf-8") == "attachment"


def test_credentials_are_loaded_without_changing_environment(tmp_path, monkeypatch):
    import pwnv.utils.remote as remote

    env_path = tmp_path / ".env"
    env_path.write_text(
        'CTF_USERNAME="second"\nCTF_PASSWORD="special value"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("CTF_USERNAME", "first")

    credentials = remote._load_credentials(env_path)

    assert credentials["username"] == "second"
    assert credentials["password"] == "special value"
    assert os.environ["CTF_USERNAME"] == "first"


def test_credentials_are_saved_with_restricted_permissions(tmp_path):
    import pwnv.utils.remote as remote

    env_path = tmp_path / ".env"
    remote._save_credentials(
        env_path,
        {"username": "user", "password": "value with spaces", "token": None},
    )

    assert remote._load_credentials(env_path)["password"] == "value with spaces"
    assert env_path.stat().st_mode & 0o777 == 0o600


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

    original = {challenge.id for challenge in get_challenges()}
    assert sync_remote_ctf(ctf)
    assert {challenge.id for challenge in get_challenges()} == original


def test_add_remote_ctf_fails_when_client_unavailable(monkeypatch, isolated_config):
    import pwnv.utils.remote as remote

    ctfs_path = get_ctfs_path()
    ctf_path = ctfs_path / "failing-ctf"
    ctf = CTF(name="FailingCTF", path=ctf_path, url="https://example.invalid")

    # Simulate inability to create a client/auth methods (network or URL failure)

    async def _no_client(url, platform=None):
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

    async def _fake_methods(url, platform=None):
        return "dummy_client", ["creds"]

    monkeypatch.setattr(remote, "get_remote_credential_methods", _fake_methods)
    monkeypatch.setattr(remote, "_ask_for_credentials", lambda methods: {})

    added = add_remote_ctf(ctf)
    assert added is False
    assert not ctf_path.exists()


def test_a_pinned_platform_is_handed_to_ctfbridge(monkeypatch):
    """Detection is asked for only when nothing was pinned."""
    import ctfbridge

    import pwnv.utils.remote as remote

    seen: dict = {}

    async def _create_client(**kwargs):
        seen.update(kwargs)
        return "client"

    monkeypatch.setattr(ctfbridge, "create_client", _create_client)

    assert remote._run_async(remote.open_client("https://ctf", "rctf")) == "client"
    assert seen == {"url": "https://ctf", "platform": "rctf"}

    remote._run_async(remote.open_client("https://ctf"))
    assert seen["platform"] == "auto"


def test_the_platform_stored_on_a_ctf_is_used_for_every_later_call(monkeypatch):
    """Pinning once is the point: it has to survive into the next command."""
    import pwnv.utils.remote as remote

    asked: list = []

    async def _open(url, platform=None):
        asked.append(platform)
        raise RuntimeError("connection refused")

    monkeypatch.setattr(remote, "open_client", _open)
    ctf = CTF(
        name="Pinned",
        path=get_ctfs_path() / "pinned",
        url="https://ctf.invalid",
        platform="rctf",
    )

    assert add_remote_ctf(ctf) is False
    assert sync_remote_ctf(ctf) is None
    assert asked == ["rctf", "rctf"]


def test_an_unknown_platform_is_rejected_with_the_ones_that_exist():
    """A typo must not be sent to ctfbridge as if it were a platform."""
    from typer.testing import CliRunner

    from pwnv import app

    result = CliRunner().invoke(
        app,
        ["ctf", "add", "Typo", "--url", "https://ctf.invalid", "--platform", "rctfd"],
    )

    assert result.exit_code == 1
    assert "Unknown platform" in result.output
    assert "rctf" in result.output


def test_sync_pins_the_platform_on_the_ctf(monkeypatch):
    """A CTF added before you knew what it was can be corrected in place."""
    from typer.testing import CliRunner

    import pwnv.utils as utils
    import pwnv.utils.remote as remote
    from pwnv import app
    from pwnv.utils import get_ctfs

    add_ctf(CTF(name="Late", path=get_ctfs_path() / "late", url="https://ctf.invalid"))
    monkeypatch.setattr(
        utils, "sync_remote_ctf", lambda ctf, **kwargs: dict(remote._EMPTY_SUMMARY)
    )

    result = CliRunner().invoke(
        app, ["ctf", "sync", "--ctf", "Late", "--platform", "RCTF"]
    )

    assert result.exit_code == 0
    assert get_ctfs()[0].platform == "rctf"
