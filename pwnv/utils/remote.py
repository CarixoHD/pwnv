"""Helpers for interacting with remote CTF platforms via ``ctfbridge``."""

import asyncio

from pwnv.models import CTF, Challenge
from pwnv.models.challenge import Category

_keyword_map = {
    "pwn": Category.pwn,
    "web": Category.web,
    "rev": Category.rev,
    "reverse": Category.rev,
    "crypto": Category.crypto,
    "cryptography": Category.crypto,
    "stego": Category.steg,
    "steganography": Category.steg,
    "misc": Category.misc,
    "miscellaneous": Category.misc,
    "osint": Category.osint,
    "forensics": Category.forensics,
    "hardware": Category.hardware,
    "mobile": Category.mobile,
    "game": Category.game,
    "blockchain": Category.blockchain,
}


def sanitize(name: str) -> str:
    """Return a filesystem friendly version of ``name``."""
    return name.strip().replace(" ", "-").replace("..", ".").replace("/", "_").lower()


def normalise_category(raw: str) -> Category:
    """Best effort mapping from a textual category to :class:`Category`."""
    import re

    clean = re.sub(r"\\(.*?\\)", "", raw).strip().lower()
    key = re.split(r"[^a-z]+", clean, maxsplit=1)[0]
    return _keyword_map.get(key, Category.other)


def _ask_for_credentials(methods) -> dict:
    """Prompt the user for credentials using available authentication methods."""
    from ctfbridge.models.auth import AuthMethod
    from InquirerPy import inquirer

    from pwnv.utils.ui import error, prompt_text

    creds = {"username": None, "password": None, "token": None}
    chosen = inquirer.select(
        message="Choose authentication method:",
        choices=[method.name for method in methods],
    ).execute()
    if chosen == AuthMethod.CREDENTIALS.name:
        creds["username"] = prompt_text("Username:")
        creds["password"] = inquirer.secret(message="Password:").execute().strip()
    elif chosen == AuthMethod.TOKEN.name:
        creds["token"] = inquirer.secret(message="Token:").execute().strip()
    else:
        error("No supported authentication methods found.")
        return {}
    return creds


_runner: asyncio.Runner | None = None


def _run_async(coro):
    """Run ``coro`` in a persistent asyncio runner."""
    import asyncio
    import atexit

    global _runner
    if _runner is None:
        _runner = asyncio.Runner()
        atexit.register(_runner.close)
    return _runner.run(coro)


def add_remote_ctf(ctf: CTF) -> None:
    """Interactively add ``ctf`` by fetching its challenges remotely."""
    from pwnv.utils.crud import add_ctf, remove_ctf

    client, methods = _run_async(get_remote_credential_methods(ctf.url))
    if client is None:
        return
    creds = _ask_for_credentials(methods)
    if not creds:
        return

    add_ctf(ctf)

    if not _run_async(create_remote_session(client, creds, ctf)):
        remove_ctf(ctf)
        return

    challenges = _run_async(get_remote_challenges(client, ctf))
    if challenges is None:
        remove_ctf(ctf)
        return

    env_path = ctf.path / ".env"
    with open(env_path, "w") as f:
        if creds.get("username", None):
            f.write(f"CTF_USERNAME={creds.get('username')}\n")
        if creds.get("password", None):
            f.write(f"CTF_PASSWORD={creds.get('password')}\n")
        if creds.get("token", None):
            f.write(f"CTF_TOKEN={creds.get('token')}\n")

    _run_async(add_remote_challenges(client, ctf, challenges))


async def get_remote_credential_methods(url: str):
    """Retrieve supported authentication methods from the remote platform."""
    from ctfbridge import create_client

    try:
        client = await create_client(url=url)
    except Exception:
        from pwnv.utils.ui import error

        error("Failed to get client.")
        return None, None
    methods = await client.auth.get_supported_auth_methods()
    return client, methods


async def create_remote_session(client, creds, ctf) -> bool:
    """Create and store an authenticated session."""
    try:
        await client.auth.login(**creds)
        await client.session.save(str(ctf.path / ".session"))
        return True
    except Exception:
        from pwnv.utils.ui import error

        error("Failed to authenticate with the provided credentials.")
        return False


async def get_remote_challenges(client, ctf):
    """Fetch the list of challenges for ``ctf`` from the remote platform."""
    try:
        await client.session.load(ctf.path / ".session")
        challenges = await client.challenges.get_all()
        return challenges
    except Exception:
        from pwnv.utils.ui import error

        error("Failed to fetch challenges.")
        return None


async def add_remote_challenges(client, ctf: CTF, challenges) -> None:
    """Persist fetched challenges locally and download attachments."""
    from pwnv.models import Challenge
    from pwnv.models.challenge import Solved
    from pwnv.utils.crud import add_challenge
    from pwnv.utils.ui import success

    for ch in challenges:
        category = normalise_category(ch.category)
        name = sanitize(ch.name)
        challenge = Challenge(
            name=name,
            ctf_id=ctf.id,
            path=ctf.path / category.name / name,
            category=category,
            points=ch.value,
            solved=Solved.solved if ch.solved else Solved.unsolved,
            extras={
                "slug": ch.id,
                "description": ch.description,
                "attachments": [att.model_dump() for att in ch.attachments],
                "author": ch.author,
            },
            tags=ch.tags,
        )
        add_challenge(challenge)
        try:
            await client.attachments.download_all(ch.attachments, challenge.path)
        except Exception:
            from pwnv.utils.ui import warn

            warn(f"Skipped attachments for {challenge.name}")

        success(f"{challenge.name} ({challenge.points} pts) added")


async def remote_solve(ctf: CTF, challenge: Challenge, flag: str) -> bool:
    """Submit ``flag`` to the remote platform and return ``True`` if correct."""
    import os

    from ctfbridge import create_client
    from dotenv import load_dotenv

    client = await create_client(ctf.url)
    if (ctf.path / ".session").exists():
        try:
            await client.session.load(ctf.path / ".session")
        except Exception as e:
            from pwnv.utils.ui import warn

            warn(f"Ignoring broken session cookie ({e}).")

    elif (ctf.path / ".env").exists():
        load_dotenv(ctf.path / ".env")
        creds = {
            "username": os.getenv("CTF_USERNAME"),
            "password": os.getenv("CTF_PASSWORD"),
            "token": os.getenv("CTF_TOKEN"),
        }
        await client.auth.login(**creds)
    else:
        creds = _ask_for_credentials(await client.auth.get_supported_auth_methods())
        if not await create_remote_session(client, creds, ctf):
            return False

    try:
        res = await client.challenges.submit(challenge.extras["slug"], flag)
        if res.correct:
            from pwnv.utils.ui import success

            success(f"Flag [cyan]{flag}[/] accepted!")

            return True
        else:
            from pwnv.utils.ui import error

            error(f"Flag [cyan]{flag}[/] incorrect")
            return False
    except Exception:
        error(f"Failed to submit flag '{flag}'.")
        return False
