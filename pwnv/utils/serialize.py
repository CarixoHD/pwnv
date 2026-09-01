"""Canonical JSON shapes for the objects the CLI reports on.

Every ``--json`` flag renders through here, so a challenge looks the same
whether it arrived from ``challenge info``, ``challenge search`` or something
written later. The values are plain JSON types - enums by name, ids and paths as
strings, solve state as a bool - because the reader is another program rather
than a person.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Sequence

if TYPE_CHECKING:
    from pwnv.models import CTF, Challenge
    from pwnv.plugins import ChallengePlugin


def _extras(challenge: Challenge) -> dict:
    extras = challenge.extras
    return extras if isinstance(extras, dict) else {}


def _mappings(value: Any) -> List[dict]:
    """Keep the mappings out of a stored list, whatever else ended up in it."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def challenge_payload(
    challenge: Challenge, *, ctf_names: Dict[Any, str] | None = None
) -> Dict[str, Any]:
    """
    Render one challenge as JSON-safe data.

    ``ctf_names`` lets a caller resolve the owning CTF once for a whole list
    instead of rescanning the config per challenge.
    """
    if ctf_names is None:
        from pwnv.utils.crud import get_ctfs

        ctf_names = {ctf.id: ctf.name for ctf in get_ctfs()}

    extras = _extras(challenge)
    return {
        "id": str(challenge.id),
        "name": challenge.name,
        "ctf": ctf_names.get(challenge.ctf_id),
        "category": challenge.category.name,
        "points": challenge.points,
        "solved": bool(challenge.solved),
        "flag": challenge.flag,
        "path": str(challenge.path),
        "tags": list(challenge.tags or []),
        "description": extras.get("description"),
        "author": extras.get("author"),
        "slug": extras.get("slug"),
        "services": _mappings(extras.get("services")),
        "attachments": _mappings(extras.get("attachments")),
    }


def challenges_payload(challenges: Sequence[Challenge]) -> List[Dict[str, Any]]:
    """Render a list of challenges, resolving CTF names once."""
    from pwnv.utils.crud import get_ctfs

    ctf_names = {ctf.id: ctf.name for ctf in get_ctfs()}
    return [challenge_payload(item, ctf_names=ctf_names) for item in challenges]


def ctf_payload(ctf: CTF) -> Dict[str, Any]:
    """Render one CTF, including the challenge counts a caller would tally."""
    from pwnv.utils.crud import challenges_for_ctf

    challenges = challenges_for_ctf(ctf)
    return {
        "id": str(ctf.id),
        "name": ctf.name,
        "path": str(ctf.path),
        "url": ctf.url,
        "running": bool(ctf.running),
        "created_at": ctf.created_at.isoformat(),
        "challenges": len(challenges),
        "solved": sum(1 for item in challenges if item.solved),
    }


def ctfs_payload(ctfs: Sequence[CTF]) -> List[Dict[str, Any]]:
    return [ctf_payload(item) for item in ctfs]


def plugin_payload(plugin: ChallengePlugin) -> Dict[str, Any]:
    """Render one plugin, minus its source - that is what the file path is for."""
    from pwnv.core.plugin_manager import plugin_name
    from pwnv.utils.plugin import get_plugin_selection, get_plugins_directory

    name = plugin_name(plugin)
    category = plugin.category().name
    return {
        "name": name,
        "category": category,
        "file": str(get_plugins_directory() / f"{name}.py"),
        "selected": get_plugin_selection().get(category) == name,
        "templates": sorted(plugin.templates_to_copy),
    }


def plugins_payload(plugins: Sequence[ChallengePlugin]) -> List[Dict[str, Any]]:
    return [plugin_payload(item) for item in plugins]


def emit_json(payload: Any) -> None:
    """Write ``payload`` to stdout as the command's entire output."""
    import json

    import typer

    typer.echo(json.dumps(payload, indent=2, default=str))
