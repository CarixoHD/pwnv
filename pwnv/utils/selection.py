"""Helpers for resolving explicit or interactive CLI selections."""

from typing import Sequence

from pwnv.models import Challenge


def resolve_challenge(
    *,
    challenge_name: str | None = None,
    ctf_name: str | None = None,
    challenges: Sequence[Challenge] | None = None,
    prompt: str = "Select a challenge:",
) -> Challenge:
    """Resolve a challenge by scope, current directory, or interactive selection."""
    import typer

    from pwnv.utils.crud import (
        challenges_for_ctf,
        get_challenges,
        get_ctf_by_name,
        get_current_challenge,
    )
    from pwnv.utils.ui import error, prompt_challenge_selection

    selected_ctf = get_ctf_by_name(ctf_name) if ctf_name else None
    if ctf_name and selected_ctf is None:
        error(f"CTF '{ctf_name}' does not exist.")
        raise typer.Exit(code=1)

    scope = (
        list(challenges)
        if challenges is not None
        else (challenges_for_ctf(selected_ctf) if selected_ctf else get_challenges())
    )
    if selected_ctf and challenges is not None:
        scope = [ch for ch in scope if ch.ctf_id == selected_ctf.id]

    if challenge_name:
        matches = [ch for ch in scope if ch.name == challenge_name]
        if not matches:
            error(f"Challenge '{challenge_name}' does not exist in the selected scope.")
            raise typer.Exit(code=1)
        if len(matches) > 1:
            error("Challenge name is ambiguous; add --ctf to select one CTF.")
            raise typer.Exit(code=1)
        return matches[0]

    current = get_current_challenge()
    if current in scope:
        return current
    return prompt_challenge_selection(scope, prompt)
