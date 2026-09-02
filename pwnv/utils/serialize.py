"""Canonical JSON payloads for the CLI's ``--json`` output."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Sequence

if TYPE_CHECKING:
    from pwnv.models import CTF, Challenge
    from pwnv.plugins import ChallengePlugin


def _extras(challenge: Challenge) -> dict:
    extras = challenge.extras
    return extras if isinstance(extras, dict) else {}


def _mappings(value: Any) -> List[dict]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def challenge_payload(
    challenge: Challenge, *, ctf_names: Dict[Any, str] | None = None
) -> Dict[str, Any]:
    """Render one challenge as JSON-safe data; ``ctf_names`` maps CTF ids to names."""
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
    """Render a list of challenges as JSON-safe data."""
    from pwnv.utils.crud import get_ctfs

    ctf_names = {ctf.id: ctf.name for ctf in get_ctfs()}
    return [challenge_payload(item, ctf_names=ctf_names) for item in challenges]


def _ctf_payload(ctf: CTF, challenges: int, solved: int) -> Dict[str, Any]:
    return {
        "id": str(ctf.id),
        "name": ctf.name,
        "path": str(ctf.path),
        "url": ctf.url,
        "platform": ctf.platform,
        "running": bool(ctf.running),
        "created_at": ctf.created_at.isoformat(),
        "challenges": challenges,
        "solved": solved,
    }


def ctf_payload(ctf: CTF) -> Dict[str, Any]:
    """Render one CTF with its challenge counts."""
    from pwnv.utils.crud import challenges_for_ctf

    challenges = challenges_for_ctf(ctf)
    return _ctf_payload(
        ctf, len(challenges), sum(1 for item in challenges if item.solved)
    )


def ctfs_payload(ctfs: Sequence[CTF]) -> List[Dict[str, Any]]:
    """Render a list of CTFs with challenge counts."""
    from collections import Counter

    from pwnv.utils.crud import get_challenges

    challenges = get_challenges()
    totals = Counter(item.ctf_id for item in challenges)
    solved = Counter(item.ctf_id for item in challenges if item.solved)
    return [_ctf_payload(item, totals[item.id], solved[item.id]) for item in ctfs]


def _plugin_payload(
    plugin: ChallengePlugin, selection: Dict[str, str], directory: Any
) -> Dict[str, Any]:
    from pwnv.core.plugin_manager import plugin_name

    name = plugin_name(plugin)
    category = plugin.category().name
    return {
        "name": name,
        "category": category,
        "file": str(directory / f"{name}.py"),
        "selected": selection.get(category) == name,
        "templates": sorted(plugin.templates_to_copy),
    }


def plugin_payload(plugin: ChallengePlugin) -> Dict[str, Any]:
    """Render one plugin as JSON-safe data."""
    from pwnv.utils.plugin import get_plugin_selection, get_plugins_directory

    return _plugin_payload(plugin, get_plugin_selection(), get_plugins_directory())


def plugins_payload(plugins: Sequence[ChallengePlugin]) -> List[Dict[str, Any]]:
    """Render a list of plugins as JSON-safe data."""
    from pwnv.utils.plugin import get_plugin_selection, get_plugins_directory

    selection = get_plugin_selection()
    directory = get_plugins_directory()
    return [_plugin_payload(item, selection, directory) for item in plugins]


def emit_json(payload: Any) -> None:
    """Write ``payload`` to stdout as the command's entire output."""
    import json

    import typer

    typer.echo(json.dumps(payload, indent=2, default=str))
