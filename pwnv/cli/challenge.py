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
def add(name: str) -> None:
    """Adds a new challenge to a selected CTF."""
    from pwnv.utils import (
        add_challenge,
        challenges_for_ctf,
        error,
        get_current_ctf,
        get_running_ctfs,
        is_duplicate,
        prompt_category_selection,
        prompt_ctf_selection,
        sanitize,
        success,
        warn,
    )

    chosen_ctf: CTF | None = get_current_ctf() or (
        prompt_ctf_selection(get_running_ctfs(), "Select a running CTF:")
        if get_running_ctfs()
        else None
    )
    if not chosen_ctf:
        warn("No running CTFs found.")
        return

    category = prompt_category_selection()
    ch_path = chosen_ctf.path / category.name / sanitize(name)

    if ch_path.exists() or is_duplicate(
        path=ch_path, model_list=challenges_for_ctf(chosen_ctf)
    ):
        error(
            f"[cyan]{name}[/] already exists in "
            f"[cyan]{chosen_ctf.name}/{category.name}/[/]."
        )
        return

    challenge = Challenge(
        ctf_id=chosen_ctf.id, name=name, path=ch_path, category=category
    )
    add_challenge(challenge)
    success(f"[cyan]{challenge.name}[/] added")


@app.command()
@config_exists()
@challenges_exists()
def remove() -> None:
    """Removes an existing challenge from a CTF."""
    from pwnv.utils import (
        challenges_for_ctf,
        get_challenges,
        get_current_ctf,
        prompt_challenge_selection,
        prompt_confirm,
        remove_challenge,
        success,
    )

    current_ctf = get_current_ctf()
    challenges: List[Challenge] = (
        challenges_for_ctf(current_ctf) if current_ctf else get_challenges()
    )
    challenge = prompt_challenge_selection(challenges, "Select a challenge to remove:")

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
) -> None:
    """Displays detailed information about a selected challenge."""
    from pwnv.utils import (
        challenges_for_ctf,
        get_challenges,
        get_ctfs,
        get_current_challenge,
        get_current_ctf,
        prompt_challenge_selection,
        prompt_confirm,
        prompt_ctf_selection,
        show_challenge,
        warn,
    )

    current = get_current_challenge()
    if current:
        show_challenge(current)
        return

    if all:
        challenges = get_challenges()
    else:
        selected_ctf = (
            get_current_ctf()
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
