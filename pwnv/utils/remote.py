"""Helpers for interacting with remote CTF platforms via ``ctfbridge``."""

import asyncio
from pathlib import Path
from typing import Any, Dict, Tuple

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
    import re

    sanitized = re.sub(r"\s+", "-", name.strip().lower())
    sanitized = re.sub(r"[/\\\x00-\x1f\x7f]", "_", sanitized)
    sanitized = re.sub(r"\.{2,}", ".", sanitized).strip(".-")
    return sanitized or "challenge"


def normalise_category(raw: str) -> Category:
    """Best effort mapping from a textual category to :class:`Category`."""
    import re

    clean = re.sub(r"\\(.*?\\)", "", raw).strip().lower()
    key = re.split(r"[^a-z]+", clean, maxsplit=1)[0]
    return _keyword_map.get(key, Category.other)


def _ask_for_credentials(methods) -> Dict[str, str | None]:
    """Prompt the user for credentials using available authentication methods."""
    from ctfbridge.models.auth import AuthMethod
    from InquirerPy import inquirer

    from pwnv.utils.ui import error, prompt_text

    creds: Dict[str, str | None] = {"username": None, "password": None, "token": None}

    if len(methods) == 1:
        chosen_method = methods[0]
    else:
        choices = [
            {"name": method.name.capitalize(), "value": method} for method in methods
        ]
        chosen_method = inquirer.select(
            message="Choose authentication method:",
            choices=choices,
        ).execute()

    if chosen_method == AuthMethod.CREDENTIALS:
        creds["username"] = prompt_text("Username:")
        creds["password"] = inquirer.secret(message="Password:").execute().strip()
    elif chosen_method == AuthMethod.TOKEN:
        creds["token"] = inquirer.secret(message="Token:").execute().strip()
    else:
        error("No supported authentication methods found.")
        return {}
    return creds


_runner: asyncio.Runner | None = None


def _load_credentials(path: Path) -> Dict[str, str | None]:
    """Load credentials from ``path`` without modifying the environment."""
    from dotenv import dotenv_values

    values = dotenv_values(path)
    return {
        "username": values.get("CTF_USERNAME"),
        "password": values.get("CTF_PASSWORD"),
        "token": values.get("CTF_TOKEN"),
    }


def _save_credentials(path: Path, creds: Dict[str, str | None]) -> None:
    """Store credentials in a user-readable dotenv file."""
    from dotenv import set_key

    path.touch(mode=0o600, exist_ok=True)
    path.chmod(0o600)
    for name, key in (
        ("username", "CTF_USERNAME"),
        ("password", "CTF_PASSWORD"),
        ("token", "CTF_TOKEN"),
    ):
        if value := creds.get(name):
            set_key(path, key, value)


def _run_async(coro):
    """Run ``coro`` in a persistent asyncio runner."""
    import asyncio
    import atexit

    global _runner
    if _runner is None:
        _runner = asyncio.Runner()
        atexit.register(_runner.close)
    return _runner.run(coro)


def add_remote_ctf(ctf: CTF, credentials: Dict[str, str | None] | None = None) -> bool:
    """Interactively add ``ctf`` by fetching its challenges remotely."""
    from pwnv.utils.crud import add_ctf, remove_ctf

    client, methods = _run_async(get_remote_credential_methods(ctf.url))
    if client is None or methods is None:
        return False
    creds = credentials or _ask_for_credentials(methods)
    if not creds:
        return False

    add_ctf(ctf)

    if not _run_async(create_remote_session(client, creds, ctf)):
        remove_ctf(ctf)
        return False

    challenges = _run_async(get_remote_challenges(client, ctf))
    if challenges is None:
        remove_ctf(ctf)
        return False

    _save_credentials(ctf.path / ".env", creds)

    _run_async(add_remote_challenges(client, ctf, challenges))
    return True


def sync_remote_ctf(ctf: CTF) -> bool:
    """Fetch new challenges for ``ctf`` from its remote platform."""
    from pwnv.utils.ui import info, warn

    if not ctf.url:
        warn("CTF has no remote URL configured.")
        return False

    client, methods = _run_async(get_remote_credential_methods(ctf.url))
    if client is None or methods is None:
        return False

    creds: Dict[str, str | None] = {}
    if (ctf.path / ".session").exists():
        try:
            _run_async(client.session.load(str(ctf.path / ".session")))
        except Exception as e:
            warn(f"Ignoring broken session cookie ({e}).")
            creds = _ask_for_credentials(methods)
            if not creds:
                return False
            if not _run_async(create_remote_session(client, creds, ctf)):
                return False
    elif (ctf.path / ".env").exists():
        creds = _load_credentials(ctf.path / ".env")
        if not _run_async(create_remote_session(client, creds, ctf)):
            return False
    else:
        creds = _ask_for_credentials(methods)
        if not creds:
            return False
        if not _run_async(create_remote_session(client, creds, ctf)):
            return False

    challenges = _run_async(get_remote_challenges(client, ctf))
    if challenges is None:
        return False

    if not challenges:
        info("No challenges found.")
        return True

    _run_async(add_remote_challenges(client, ctf, challenges))
    return True


async def get_remote_credential_methods(
    url: str | None,
) -> Tuple[Any, Any] | Tuple[None, None]:
    """Retrieve supported authentication methods from the remote platform."""
    from ctfbridge import create_client

    if not url:
        return None, None

    try:
        client: Any = await create_client(url=url)
    except Exception:
        from pwnv.utils.ui import error

        error("Failed to get client.")
        return None, None
    methods = await client.auth.get_supported_auth_methods()
    return client, methods


async def create_remote_session(
    client: Any, creds: Dict[str, str | None], ctf: CTF
) -> bool:
    """Create and store an authenticated session."""
    try:
        await client.auth.login(**{k: v for k, v in creds.items() if v is not None})
        await client.session.save(str(ctf.path / ".session"))
        return True
    except Exception:
        from pwnv.utils.ui import error

        error("Failed to authenticate with the provided credentials.")
        return False


async def get_remote_challenges(client: Any, ctf: CTF):
    """Fetch the list of challenges for ``ctf`` from the remote platform."""
    try:
        await client.session.load(str(ctf.path / ".session"))
        challenges = await client.challenges.get_all()
        return challenges
    except Exception:
        from pwnv.utils.ui import error

        error("Failed to fetch challenges.")
        return None


async def add_remote_challenges(client, ctf: CTF, challenges) -> None:
    """Create or update fetched challenges and download their attachments."""
    from pwnv.models import Challenge
    from pwnv.models.challenge import Solved
    from pwnv.utils.crud import add_challenge, challenges_for_ctf, update_challenge
    from pwnv.utils.ui import success

    existing_challenges = challenges_for_ctf(ctf)
    for ch in challenges:
        category = normalise_category(ch.category)
        name = sanitize(ch.name)
        existing = next(
            (
                item
                for item in existing_challenges
                if (isinstance(item.extras, dict) and item.extras.get("slug") == ch.id)
                or sanitize(item.name) == name
            ),
            None,
        )
        path = existing.path if existing else ctf.path / category.name / name

        try:
            ch = await client.attachments.download_all(ch, save_dir=path)
        except Exception:
            from pwnv.utils.ui import warn

            warn(f"Skipped attachments for {name}")

        attachments = [
            att.model_dump(mode="json") for att in getattr(ch, "attachments", [])
        ]
        services = [svc.model_dump(mode="json") for svc in getattr(ch, "services", [])]

        extras = {
            **(existing.extras if existing and existing.extras else {}),
            **{
                "slug": ch.id,
                "description": ch.description,
                "attachments": attachments,
                "services": services,
                "author": ch.author,
            },
        }
        if existing:
            existing.category = category
            existing.points = ch.value
            existing.solved = Solved.solved if ch.solved else existing.solved
            existing.extras = extras
            existing.tags = sorted(set(existing.tags or []) | set(ch.tags or []))
            update_challenge(existing)
            success(f"{existing.name} ({existing.points} pts) updated")
            continue

        challenge = Challenge(
            name=name,
            ctf_id=ctf.id,
            path=path,
            category=category,
            points=ch.value,
            solved=Solved.solved if ch.solved else Solved.unsolved,
            extras=extras,
            tags=ch.tags,
        )
        add_challenge(challenge)
        existing_challenges.append(challenge)

        success(f"{challenge.name} ({challenge.points} pts) added")


async def remote_solve(ctf: CTF, challenge: Challenge, flag: str) -> bool:
    """Submit ``flag`` to the remote platform and return ``True`` if correct."""
    from ctfbridge import create_client

    if not ctf.url:
        return False

    client: Any = await create_client(ctf.url)
    if (ctf.path / ".session").exists():
        try:
            await client.session.load(str(ctf.path / ".session"))
        except Exception as e:
            from pwnv.utils.ui import warn

            warn(f"Ignoring broken session cookie ({e}).")

    elif (ctf.path / ".env").exists():
        creds = _load_credentials(ctf.path / ".env")
        await client.auth.login(**{k: v for k, v in creds.items() if v is not None})
    else:
        creds = _ask_for_credentials(await client.auth.get_supported_auth_methods())
        if not await create_remote_session(client, creds, ctf):
            return False

    try:
        slug = (
            challenge.extras.get("slug") if isinstance(challenge.extras, dict) else None
        )
        if slug is None:
            return False
        res = await client.challenges.submit(slug, flag)
        if res.correct:
            from pwnv.utils.ui import success

            success(f"Flag [cyan]{flag}[/] accepted!")

            return True
        else:
            from pwnv.utils.ui import error

            error(f"Flag [cyan]{flag}[/] incorrect")
            return False
    except Exception:
        from pwnv.utils.ui import error

        error(f"Failed to submit flag '{flag}'.")
        return False
