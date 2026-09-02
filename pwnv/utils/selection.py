from typing import List, Sequence

from pwnv.models import Challenge


def _narrow_to_likeliest(matches: List[Challenge]) -> List[Challenge]:
    from pwnv.utils.crud import get_current_ctf, get_running_ctfs

    if len(matches) < 2:
        return matches

    current = get_current_ctf()
    if current and (local := [ch for ch in matches if ch.ctf_id == current.id]):
        return local

    running = {ctf.id for ctf in get_running_ctfs()}
    return [ch for ch in matches if ch.ctf_id in running] or matches


def _matching(scope: Sequence[Challenge], name: str) -> List[Challenge]:
    from pwnv.utils.remote import sanitize

    needle = name.strip()
    folded = needle.casefold()
    slug = sanitize(needle)

    for candidates in (
        [ch for ch in scope if ch.name == needle],
        [ch for ch in scope if ch.name.casefold() == folded],
        [ch for ch in scope if sanitize(ch.name) == slug],
        [ch for ch in scope if folded in ch.name.casefold()],
    ):
        if candidates:
            return candidates
    return []


def resolve_challenge(
    *,
    challenge_name: str | None = None,
    ctf_name: str | None = None,
    challenges: Sequence[Challenge] | None = None,
    prompt: str = "Select a challenge:",
) -> Challenge:
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
        matches = _matching(scope, challenge_name)
        if not matches:
            error(f"Challenge '{challenge_name}' does not exist in the selected scope.")
            raise typer.Exit(code=1)
        matches = _narrow_to_likeliest(matches)
        if len(matches) == 1:
            return matches[0]
        return prompt_challenge_selection(
            matches, f"Multiple challenges match '{challenge_name}':"
        )

    current = get_current_challenge()
    if current in scope:
        return current
    return prompt_challenge_selection(scope, prompt)
