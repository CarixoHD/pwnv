"""The challenge you are standing in, as the object ctfbridge already defines.

``pwnv challenge path`` answers "which challenge is this?" for the shell. This
answers it for Python, so a solve script reads ``challenge.service.host``
instead of a host that was baked into the file at scaffold time.

The distinction matters during an event.
:func:`pwnv.utils.template.render_template` substitutes ``{{service.host}}``
once, when the file is written, and leaves the token untouched when it cannot
resolve - so a challenge scaffolded before the first sync ends up with the
literal in it, and a service that moves later strands every script already on
disk. Reading it here binds the value at run time instead.

What comes back is a :class:`ctfbridge.models.challenge.Challenge`, rebuilt from
the workspace: the same object the sync fetched, with the same fields, helpers
and serialisers. ``path`` is the only thing added, since a script started from
elsewhere still has to find its own files.
"""

from __future__ import annotations

from pathlib import Path

from ctfbridge.models.challenge import AttachmentCollection, Challenge

__all__ = ["LocalChallenge", "NoChallengeError", "current"]


class NoChallengeError(RuntimeError):
    """Raised when the working directory does not belong to any challenge."""


class LocalChallenge(Challenge):
    """A ctfbridge challenge that also knows where it lives on disk."""

    path: Path
    flag: str | None = None


def current(path: Path | None = None) -> LocalChallenge:
    """
    Return the challenge that owns ``path``, or the working directory.

    :raises NoChallengeError: when the directory belongs to no challenge.
    """
    from pwnv.models.challenge import Solved
    from pwnv.utils.config import _invalidate_cache
    from pwnv.utils.crud import get_current_challenge

    _invalidate_cache()
    where = Path(path) if path is not None else Path.cwd()
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
        attachments=AttachmentCollection(attachments=extras.get("attachments") or []),
        services=extras.get("services") or [],
        tags=list(record.tags or []),
        solved=record.solved == Solved.solved,
        authors=[author] if author else [],
        path=record.path,
        flag=record.flag,
    )
