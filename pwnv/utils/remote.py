"""Helpers for interacting with remote CTF platforms via ``ctfbridge``."""

import asyncio
from pathlib import Path
from typing import Any, Dict, Tuple

from pwnv.models import CTF, Challenge
from pwnv.models.challenge import Category

_keyword_map: "list[tuple[str, Category]]" = [
    ("web exploitation", Category.web),
    ("web exploit", Category.web),
    ("binary exploitation", Category.pwn),
    ("smart contract", Category.blockchain),
    ("reverse engineering", Category.rev),
    ("exploitation", Category.pwn),
    ("pwnable", Category.pwn),
    ("pwn", Category.pwn),
    ("binex", Category.pwn),
    ("blockchain", Category.blockchain),
    ("web3", Category.blockchain),
    ("defi", Category.blockchain),
    ("web", Category.web),
    ("reverse", Category.rev),
    ("reversing", Category.rev),
    ("rev", Category.rev),
    ("re", Category.rev),
    ("cryptography", Category.crypto),
    ("crypto", Category.crypto),
    ("steganography", Category.steg),
    ("stego", Category.steg),
    ("steg", Category.steg),
    ("forensics", Category.forensics),
    ("forensic", Category.forensics),
    ("df/ir", Category.forensics),
    ("dfir", Category.forensics),
    ("osint", Category.osint),
    ("recon", Category.osint),
    ("hardware", Category.hardware),
    ("embedded", Category.hardware),
    ("radio", Category.hardware),
    ("sdr", Category.hardware),
    ("ics", Category.hardware),
    ("mobile", Category.mobile),
    ("android", Category.mobile),
    ("ios", Category.mobile),
    ("game", Category.game),
    ("gaming", Category.game),
    ("miscellaneous", Category.misc),
    ("misc", Category.misc),
    ("warmup", Category.misc),
    ("sanity", Category.misc),
    ("intro", Category.misc),
    ("beginner", Category.misc),
]


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

    if not raw:
        return Category.other

    clean = re.sub(r"[^a-z0-9]+", " ", raw.lower()).strip()
    if not clean:
        return Category.other

    for keyword, category in _keyword_map:
        if clean == keyword:
            return category

    for keyword, category in _keyword_map:
        if " " in keyword and keyword in clean:
            return category

    tokens = clean.split()
    for keyword, category in _keyword_map:
        if " " not in keyword and keyword in tokens:
            return category

    for keyword, category in _keyword_map:
        if len(keyword) >= 3 and " " not in keyword and keyword in clean:
            return category

    return Category.other


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


def protect_ctf_secrets(ctf_path: Path) -> None:
    """
    Drop a ``.gitignore`` next to a CTF's credentials.
    """
    gitignore = ctf_path / ".gitignore"
    entries = (".env", ".session", ".venv/", ".pwnvenv/")
    try:
        existing = (
            gitignore.read_text(encoding="utf-8").splitlines()
            if gitignore.is_file()
            else []
        )
        missing = [entry for entry in entries if entry not in existing]
        if not missing:
            return
        ctf_path.mkdir(parents=True, exist_ok=True)
        lines = existing + missing if existing else list(entries)
        gitignore.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        pass


def _save_credentials(path: Path, creds: Dict[str, str | None]) -> None:
    """Store credentials in a user-readable dotenv file."""
    from dotenv import set_key

    path.parent.mkdir(parents=True, exist_ok=True)
    protect_ctf_secrets(path.parent)
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

    client, methods = _run_async(get_remote_credential_methods(ctf.url, ctf.platform))
    if client is None or methods is None:
        return False
    creds = credentials or _ask_for_credentials(methods)
    if not creds:
        return False

    preexisting_dir = ctf.path.exists()

    add_ctf(ctf)

    def _rollback() -> None:
        if preexisting_dir:
            from pwnv.utils.config import config_transaction
            from pwnv.utils.ui import warn

            with config_transaction() as cfg:
                cfg["ctfs"] = [
                    item for item in cfg.get("ctfs", []) if item["id"] != str(ctf.id)
                ]
            warn(f"Left the existing directory {ctf.path} untouched.")
        else:
            remove_ctf(ctf)

    if not _run_async(create_remote_session(client, creds, ctf)):
        _rollback()
        return False

    challenges = _run_async(get_remote_challenges(client, ctf))
    if challenges is None:
        _rollback()
        return False

    _save_credentials(ctf.path / ".env", creds)

    _run_async(add_remote_challenges(client, ctf, challenges))
    return True


_EMPTY_SUMMARY: Dict[str, Any] = {
    "added": [],
    "updated": [],
    "unchanged": 0,
    "attachments_downloaded": [],
    "attachments_reused": [],
}


def sync_remote_ctf(
    ctf: CTF, *, refresh_attachments: bool = False, report: bool = True
) -> Dict[str, Any] | None:
    """
    Fetch new challenges for ``ctf`` from its remote platform.

    Returns a summary of what changed, or ``None`` when the sync failed.
    """
    from pwnv.utils.ui import info, warn

    if not ctf.url:
        warn("CTF has no remote URL configured.")
        return None

    client, methods = _run_async(get_remote_credential_methods(ctf.url, ctf.platform))
    if client is None or methods is None:
        return None

    creds: Dict[str, str | None] = {}
    if (ctf.path / ".session").exists():
        try:
            _run_async(client.session.load(str(ctf.path / ".session")))
        except Exception as e:
            warn(f"Ignoring broken session cookie ({e}).")
            creds = _ask_for_credentials(methods)
            if not creds:
                return None
            if not _run_async(create_remote_session(client, creds, ctf)):
                return None
    elif (ctf.path / ".env").exists():
        creds = _load_credentials(ctf.path / ".env")
        if not _run_async(create_remote_session(client, creds, ctf)):
            return None
    else:
        creds = _ask_for_credentials(methods)
        if not creds:
            return None
        if not _run_async(create_remote_session(client, creds, ctf)):
            return None

    challenges = _run_async(get_remote_challenges(client, ctf))
    if challenges is None:
        challenges = _retry_with_stored_credentials(client, ctf)
    if challenges is None:
        return None

    if not challenges:
        info("No challenges found.")
        return dict(_EMPTY_SUMMARY)

    return _run_async(
        add_remote_challenges(
            client,
            ctf,
            challenges,
            refresh_attachments=refresh_attachments,
            report=report,
        )
    )


def _stored_credentials(ctf: CTF) -> Dict[str, str | None]:
    """Return credentials saved for ``ctf``, if any."""
    env_path = ctf.path / ".env"
    if not env_path.exists():
        return {}
    creds = _load_credentials(env_path)
    return creds if any(creds.values()) else {}


def _retry_with_stored_credentials(client: Any, ctf: CTF):
    """Re-login with saved credentials and refetch challenges once."""
    from pwnv.utils.ui import info

    creds = _stored_credentials(ctf)
    if not creds:
        return None

    info("Session looks expired - re-authenticating with stored credentials.")
    if not _run_async(create_remote_session(client, creds, ctf)):
        return None
    return _run_async(get_remote_challenges(client, ctf))


def known_platforms() -> list[str]:
    """The platform names ctfbridge can be pinned to, in alphabetical order."""
    from ctfbridge.platforms.registry import PLATFORM_CLIENTS

    return sorted(PLATFORM_CLIENTS)


async def open_client(url: str, platform: str | None = None) -> Any:
    """
    Connect to ``url``, detecting the platform unless one was pinned.

    ctfbridge sniffs the platform from the site, and the sniff is a guess: an
    instance behind a proxy, or one whose landing page was themed, can come out
    as the wrong platform or as none at all. ``platform`` is the way past that,
    and it is stored on the CTF so every later sync uses it too.
    """
    from ctfbridge import create_client

    return await create_client(url=url, platform=platform or "auto")


async def get_remote_credential_methods(
    url: str | None,
    platform: str | None = None,
) -> Tuple[Any, Any] | Tuple[None, None]:
    """Retrieve supported authentication methods from the remote platform."""
    if not url:
        return None, None

    try:
        client: Any = await open_client(url, platform)
    except Exception as exc:
        from pwnv.utils.ui import command, debug_traceback, error, info

        error(f"Could not open a client for {url}: {exc}")
        if not platform:
            info(
                "If the platform was not recognised, name it: "
                f"{command('pwnv ctf add NAME --url URL --platform rctf')}."
            )
        debug_traceback()
        return None, None
    methods = await client.auth.get_supported_auth_methods()
    return client, methods


async def create_remote_session(
    client: Any, creds: Dict[str, str | None], ctf: CTF
) -> bool:
    """Create and store an authenticated session."""
    try:
        await client.auth.login(**{k: v for k, v in creds.items() if v is not None})
        ctf.path.mkdir(parents=True, exist_ok=True)
        protect_ctf_secrets(ctf.path)
        await client.session.save(str(ctf.path / ".session"))
        return True
    except Exception:
        from pwnv.utils.ui import debug_traceback, error

        error("Failed to authenticate with the provided credentials.")
        debug_traceback()
        return False


async def get_remote_challenges(client: Any, ctf: CTF):
    """Fetch the list of challenges for ``ctf`` from the remote platform."""
    try:
        await client.session.load(str(ctf.path / ".session"))
        challenges = await client.challenges.get_all()
        return challenges
    except Exception:
        from pwnv.utils.ui import debug_traceback, error

        error("Failed to fetch challenges.")
        debug_traceback()
        return None


def _slug_of(challenge: Challenge) -> Any:
    """Return the remote id recorded for ``challenge``, if it has one."""
    return challenge.extras.get("slug") if isinstance(challenge.extras, dict) else None


def _file_digest(path: Path) -> str | None:
    """Return the sha256 of ``path``, or ``None`` if it cannot be read."""
    import hashlib

    try:
        with open(path, "rb") as handle:
            return hashlib.file_digest(handle, "sha256").hexdigest()
    except OSError:
        return None


def _fingerprint_attachments(attachments) -> "list[dict]":
    """Dump attachments, recording a digest of whatever landed on disk."""
    dumped = []
    for attachment in attachments:
        data = attachment.model_dump(mode="json")
        local = data.get("local_path")
        if local and (digest := _file_digest(Path(local))):
            data["sha256"] = digest
        dumped.append(data)
    return dumped


def _attachments_are_current(remote, stored) -> bool:
    """
    Report whether every published attachment is already on disk, byte for byte.

    Platforms do not publish checksums, so the comparison is against a digest
    pwnv recorded at download time. Size is checked first because it is free.
    Re-downloading 40 MB of images on every poll is the thing to avoid here.
    """
    if not remote:
        return True

    by_name = {str(item.get("name")): item for item in stored if isinstance(item, dict)}
    for attachment in remote:
        entry = by_name.get(str(getattr(attachment, "name", "")))
        if entry is None:
            return False
        local = entry.get("local_path")
        digest = entry.get("sha256")
        if not local or not digest:
            return False
        size = getattr(attachment, "size_bytes", None)
        if size is not None and entry.get("size_bytes") not in (None, size):
            return False
        local_path = Path(local)
        if not local_path.is_file() or _file_digest(local_path) != digest:
            return False
    return True


def _unique_challenge_path(preferred: Path, taken: "list[Challenge]") -> Path:
    """Return ``preferred``, suffixed if another challenge already claims it."""
    claimed = {item.path for item in taken}
    if preferred not in claimed:
        return preferred
    for suffix in range(2, 100):
        candidate = preferred.with_name(f"{preferred.name}-{suffix}")
        if candidate not in claimed:
            return candidate
    return preferred


async def add_remote_challenges(
    client,
    ctf: CTF,
    challenges,
    *,
    refresh_attachments: bool = False,
    report: bool = True,
) -> Dict[str, Any]:
    """
    Create or update fetched challenges and download their attachments.

    Returns a summary of what changed so callers can show a diff instead of
    replaying every challenge on every sync.
    """
    from pwnv.models import Challenge
    from pwnv.models.challenge import Solved
    from pwnv.utils.crud import add_challenge, challenges_for_ctf, update_challenge
    from pwnv.utils.ui import success, warn

    summary: Dict[str, Any] = {
        "added": [],
        "updated": [],
        "unchanged": 0,
        "attachments_downloaded": [],
        "attachments_reused": [],
    }

    existing_challenges = challenges_for_ctf(ctf)
    for ch in challenges:
        category = normalise_category(ch.category)
        name = ch.name or sanitize(ch.name)
        slug_dir = sanitize(ch.name)
        existing = None
        if ch.id is not None:
            existing = next(
                (item for item in existing_challenges if _slug_of(item) == ch.id),
                None,
            )
        if existing is None:
            existing = next(
                (
                    item
                    for item in existing_challenges
                    if _slug_of(item) is None and sanitize(item.name) == slug_dir
                ),
                None,
            )

        if existing is not None:
            path = existing.path
        else:
            path = _unique_challenge_path(
                ctf.path / category.name / slug_dir, existing_challenges
            )

        old_extras = (
            existing.extras
            if existing is not None and isinstance(existing.extras, dict)
            else {}
        )
        stored_attachments = old_extras.get("attachments") or []
        remote_attachments = list(getattr(ch, "attachments", None) or [])
        reuse = not refresh_attachments and _attachments_are_current(
            remote_attachments, stored_attachments
        )

        if reuse:
            attachments = stored_attachments
            if remote_attachments:
                summary["attachments_reused"].append(name)
        else:
            try:
                ch = await client.attachments.download_all(ch, save_dir=path)
            except Exception:
                from pwnv.utils.ui import debug_traceback

                warn(f"Skipped attachments for {name}")
                debug_traceback()
            attachments = _fingerprint_attachments(
                getattr(ch, "attachments", None) or []
            )
            if attachments:
                summary["attachments_downloaded"].append(name)

        services = [svc.model_dump(mode="json") for svc in getattr(ch, "services", [])]

        extras = {
            **old_extras,
            **{
                "slug": ch.id,
                "description": ch.description,
                "attachments": attachments,
                "services": services,
                "author": ch.author,
            },
        }
        if existing:
            changes = []
            if existing.points != ch.value:
                changes.append(f"{existing.points} -> {ch.value} pts")
            if ch.solved and existing.solved != Solved.solved:
                changes.append("solved on platform")
            if existing.category != category:
                changes.append(f"{existing.category.name} -> {category.name}")
            if existing.name != name:
                changes.append(f"renamed from '{existing.name}'")
            if (ch.description or None) != (old_extras.get("description") or None):
                changes.append("description changed")
            if not reuse and remote_attachments:
                changes.append("attachments updated")
            if new_tags := set(ch.tags or []) - set(existing.tags or []):
                changes.append("new tags: " + ", ".join(sorted(new_tags)))

            existing.name = name
            existing.category = category
            existing.points = ch.value
            existing.solved = Solved.solved if ch.solved else existing.solved
            existing.extras = extras
            existing.tags = sorted(set(existing.tags or []) | set(ch.tags or []))
            update_challenge(existing)
            if changes:
                summary["updated"].append({"name": name, "changes": changes})
            else:
                summary["unchanged"] += 1
            if report:
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
        summary["added"].append(name)
        if report:
            success(f"{challenge.name} ({challenge.points} pts) added")

    return summary


async def remote_solve(ctf: CTF, challenge: Challenge, flag: str) -> bool:
    """Submit ``flag`` to the remote platform and return ``True`` if correct."""
    if not ctf.url:
        return False

    slug = challenge.extras.get("slug") if isinstance(challenge.extras, dict) else None
    if slug is None:
        from pwnv.utils.ui import error

        error(
            f"'{challenge.name}' has no remote id - it was created locally, "
            "so there is nothing to submit to. Run `pwnv ctf sync` first."
        )
        return False

    client: Any = await open_client(ctf.url, ctf.platform)
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

    async def _submit() -> bool:
        res = await client.challenges.submit(slug, flag)
        if res.correct:
            from pwnv.utils.ui import success

            success(f"Flag [cyan]{flag}[/] accepted!")
            return True
        from pwnv.utils.ui import error

        error(f"Flag [cyan]{flag}[/] incorrect")
        return False

    try:
        return await _submit()
    except Exception:
        pass

    creds = _stored_credentials(ctf)
    if creds and await create_remote_session(client, creds, ctf):
        try:
            return await _submit()
        except Exception:
            pass

    from pwnv.utils.ui import debug_traceback, error

    error(f"Failed to submit flag '{flag}'.")
    debug_traceback()
    return False
