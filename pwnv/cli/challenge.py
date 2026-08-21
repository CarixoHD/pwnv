from typing import List

import typer

from pwnv.models import CTF, Challenge
from pwnv.utils import (
    challenges_exists,
    config_exists,
    ctfs_exists,
)

app = typer.Typer(
    no_args_is_help=True,
    help=(
        "Manage challenges within your CTFs, including adding, removing, "
        "and viewing information."
    ),
)


@app.command()
@config_exists()
@ctfs_exists()
def add(
    name: str,
    ctf: str | None = typer.Option(None, "--ctf", help="CTF name (skips selection)"),
    category: str | None = typer.Option(
        None, "--category", help="Challenge category (skips selection)"
    ),
) -> None:
    """Adds a new challenge to a selected CTF."""
    from pwnv.models.challenge import Category
    from pwnv.utils import (
        add_challenge,
        challenges_for_ctf,
        error,
        get_ctf_by_name,
        get_current_ctf,
        get_running_ctfs,
        is_duplicate,
        prompt_category_selection,
        prompt_ctf_selection,
        sanitize,
        success,
        warn,
    )

    named_ctf = get_ctf_by_name(ctf) if ctf else None
    if ctf and named_ctf is None:
        error(f"CTF '{ctf}' does not exist.")
        raise typer.Exit(code=1)

    chosen_ctf: CTF | None = (
        named_ctf
        or get_current_ctf()
        or (
            prompt_ctf_selection(get_running_ctfs(), "Select a running CTF:")
            if get_running_ctfs()
            else None
        )
    )
    if not chosen_ctf:
        warn("No running CTFs found.")
        return

    if category:
        try:
            chosen_category = Category[category.lower()]
        except KeyError:
            choices = ", ".join(item.name for item in Category)
            error(f"Unknown category '{category}'. Choose one of: {choices}.")
            raise typer.Exit(code=1)
    else:
        chosen_category = prompt_category_selection()
    ch_path = chosen_ctf.path / chosen_category.name / sanitize(name)

    if ch_path.exists() or is_duplicate(
        path=ch_path, model_list=challenges_for_ctf(chosen_ctf)
    ):
        error(
            f"[cyan]{name}[/] already exists in "
            f"[cyan]{chosen_ctf.name}/{chosen_category.name}/[/]."
        )
        return

    challenge = Challenge(
        ctf_id=chosen_ctf.id, name=name, path=ch_path, category=chosen_category
    )
    add_challenge(challenge)
    success(f"[cyan]{challenge.name}[/] added")


@app.command()
@config_exists()
@challenges_exists()
def remove(
    challenge_name: str | None = typer.Option(
        None, "--challenge", help="Challenge name (skips selection)"
    ),
    ctf: str | None = typer.Option(None, "--ctf", help="Limit selection to one CTF"),
) -> None:
    """Removes an existing challenge from a CTF."""
    from pwnv.utils import (
        challenges_for_ctf,
        error,
        get_challenges,
        get_ctf_by_name,
        get_current_ctf,
        prompt_challenge_selection,
        prompt_confirm,
        remove_challenge,
        success,
    )

    selected_ctf = get_ctf_by_name(ctf) if ctf else None
    if ctf and selected_ctf is None:
        error(f"CTF '{ctf}' does not exist.")
        raise typer.Exit(code=1)
    current_ctf = selected_ctf or get_current_ctf()
    challenges: List[Challenge] = (
        challenges_for_ctf(current_ctf) if current_ctf else get_challenges()
    )
    named = [ch for ch in challenges if ch.name == challenge_name]
    if challenge_name and not named:
        error(f"Challenge '{challenge_name}' does not exist in the selected scope.")
        raise typer.Exit(code=1)
    if len(named) > 1:
        error("Challenge name is ambiguous; add --ctf to select one CTF.")
        raise typer.Exit(code=1)
    challenge = (
        named[0]
        if named
        else prompt_challenge_selection(challenges, "Select a challenge to remove:")
    )

    if challenge.path.exists() and any(challenge.path.iterdir()):
        if not prompt_confirm("Directory not empty. Remove anyway?", default=False):
            return

    remove_challenge(challenge)
    success(f"[cyan]{challenge.name}[/] removed")


@app.command(name="info")
@config_exists()
@challenges_exists()
def info_(
    all: bool = typer.Option(
        False, "--all", "-a", help="Show challenges from all CTFs"
    ),
    challenge_name: str | None = typer.Option(
        None, "--challenge", help="Challenge name (skips selection)"
    ),
    ctf: str | None = typer.Option(None, "--ctf", help="Limit selection to one CTF"),
) -> None:
    """Displays detailed information about a selected challenge."""
    from pwnv.utils import (
        challenges_for_ctf,
        error,
        get_challenges,
        get_ctf_by_name,
        get_ctfs,
        get_current_challenge,
        get_current_ctf,
        prompt_challenge_selection,
        prompt_confirm,
        prompt_ctf_selection,
        show_challenge,
        warn,
    )

    selected_ctf = get_ctf_by_name(ctf) if ctf else None
    if ctf and selected_ctf is None:
        error(f"CTF '{ctf}' does not exist.")
        raise typer.Exit(code=1)
    scope = challenges_for_ctf(selected_ctf) if selected_ctf else get_challenges()
    named = [ch for ch in scope if ch.name == challenge_name]
    if challenge_name and not named:
        error(f"Challenge '{challenge_name}' does not exist in the selected scope.")
        raise typer.Exit(code=1)
    if len(named) > 1:
        error("Challenge name is ambiguous; add --ctf to select one CTF.")
        raise typer.Exit(code=1)
    if named:
        show_challenge(named[0])
        return

    current = get_current_challenge()
    if current:
        show_challenge(current)
        return

    if all:
        challenges = get_challenges()
    else:
        selected_ctf = (
            selected_ctf
            or get_current_ctf()
            or prompt_ctf_selection(get_ctfs(), "Select a CTF:")
        )
        challenges = challenges_for_ctf(selected_ctf)

    if not challenges:
        warn("No challenges found.")
        return

    while True:
        show_challenge(prompt_challenge_selection(challenges, "Select a challenge:"))
        if not prompt_confirm("Show another?", default=False):
            break


@app.command(name="filter")
@config_exists()
@challenges_exists()
def filter_() -> None:
    """Filters and displays solved challenges based on selected tags."""
    from pwnv.utils import (
        get_solved_challenges,
        prompt_challenge_selection,
        prompt_confirm,
        prompt_tags_selection,
        show_challenge,
        warn,
    )

    solved = get_solved_challenges()
    if not solved:
        warn("No solved challenges found.")
        return

    while True:
        tags = prompt_tags_selection("Select tags to filter by:")
        subset = [ch for ch in solved if ch.tags and any(t in ch.tags for t in tags)]
        if not subset:
            warn("No challenges match your tags.")
        else:
            show_challenge(prompt_challenge_selection(subset, "Select a challenge:"))
        if not prompt_confirm("Filter again?", default=False):
            break


@app.command()
@config_exists()
@challenges_exists()
def search(
    query: str = typer.Argument("", help="Text to search for"),
    ctf: str | None = typer.Option(None, "--ctf", help="Limit results to one CTF"),
    category: str | None = typer.Option(None, "--category"),
    tag: list[str] | None = typer.Option(
        None, "--tag", help="Required tag; repeatable"
    ),
    min_points: int | None = typer.Option(None, "--min-points", min=0),
    max_points: int | None = typer.Option(None, "--max-points", min=0),
    has_service: bool | None = typer.Option(
        None, "--has-service/--no-service", help="Filter by remote service availability"
    ),
    solved: bool | None = typer.Option(
        None, "--solved/--unsolved", help="Filter by solve state"
    ),
) -> None:
    """Search challenge names, descriptions, categories, and tags."""
    from pwnv.utils import (
        challenges_for_ctf,
        error,
        get_challenges,
        get_ctf_by_name,
        search_challenges,
        show_challenge,
        warn,
    )

    selected_ctf = get_ctf_by_name(ctf) if ctf else None
    if ctf and selected_ctf is None:
        error(f"CTF '{ctf}' does not exist.")
        raise typer.Exit(code=1)

    challenges = challenges_for_ctf(selected_ctf) if selected_ctf else get_challenges()
    matches = search_challenges(
        query,
        challenges,
        category=category,
        tags=tag,
        min_points=min_points,
        max_points=max_points,
        has_service=has_service,
        solved=solved,
    )
    if not matches:
        warn(f"No challenges match '{query or 'the selected filters'}'.")
        return

    for challenge in matches:
        show_challenge(challenge)
