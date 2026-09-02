"""Programmatic access to the current challenge.

:func:`current` rebuilds the :class:`ctfbridge.models.challenge.Challenge` the
sync stored for the working directory, with ``path`` and ``flag`` added.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ctfbridge.models.challenge import AttachmentCollection, Challenge

__all__ = ["LocalChallenge", "NoChallengeError", "current"]


class NoChallengeError(RuntimeError):
    """Raised when the working directory does not belong to any challenge."""


def _mappings(value: object) -> list[Any]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


class LocalChallenge(Challenge):
    """A ctfbridge challenge that also knows where it lives on disk."""

    path: Path
    flag: str | None = None


def current(path: Path | None = None) -> LocalChallenge:
    """Return the challenge that owns ``path``, or the working directory.

    Raises :class:`NoChallengeError` when the directory belongs to no challenge.
    """
    from pwnv.models.challenge import Solved
    from pwnv.utils.config import invalidate_cache
    from pwnv.utils.crud import get_current_challenge

    invalidate_cache()
    where = (Path(path) if path is not None else Path.cwd()).expanduser().resolve()
    record = get_current_challenge(where)
    if record is None:
        raise NoChallengeError(
            f"{where} is not inside a pwnv challenge directory. Run this from a "
            "challenge, or create one with `pwnv challenge add`."
        )

    extras = record.extras if isinstance(record.extras, dict) else {}
    author = extras.get("author")
    return LocalChallenge(
        id=str(extras.get("slug") or record.id),
        name=record.name,
        categories=[record.category.name],
        value=record.points,
        description=extras.get("description"),
        attachments=AttachmentCollection(
            attachments=_mappings(extras.get("attachments"))
        ),
        services=_mappings(extras.get("services")),
        tags=list(record.tags or []),
        solved=record.solved == Solved.solved,
        authors=[author] if author else [],
        path=record.path,
        flag=record.flag,
    )
