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
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt"),
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

    if not yes and challenge.path.exists() and any(challenge.path.iterdir()):
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
    filters = (category, tag, min_points, max_points, has_service, solved)
    if not query and not any(value is not None and value != [] for value in filters):
        # A bare `search --ctf X` used to return nothing, because the underlying
        # helper treats "no query and no filter" as an empty result. Naming a
        # scope is itself a request to see it.
        matches = list(challenges)
    else:
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


@app.command()
@config_exists()
@challenges_exists()
def scaffold(
    challenge_name: str | None = typer.Option(
        None, "--challenge", help="Challenge name (skips selection)"
    ),
    ctf: str | None = typer.Option(None, "--ctf", help="Limit selection to one CTF"),
    category: str | None = typer.Option(
        None,
        "--category",
        help="Template category to apply (defaults to the challenge's own)",
    ),
    plugin: str | None = typer.Option(
        None, "--plugin", help="Apply a specific plugin by name"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite files that already exist"
    ),
    suffix: str = typer.Option(
        "",
        "--suffix",
        help="Append to every written filename, e.g. --suffix _pwn -> solve_pwn.py",
    ),
) -> None:
    """
    Re-run a plugin's template and setup for an existing challenge.

    The plugin is chosen independently of the challenge, so you can drop the pwn
    template into a web challenge. Nothing about the challenge itself changes.
    """
    from pwnv.core.plugin_manager import plugin_manager
    from pwnv.models.challenge import Category
    from pwnv.plugins import template_write_policy
    from pwnv.utils import (
        error,
        get_selected_plugin_for_category,
        info,
        prompt_category_selection,
        resolve_challenge,
        success,
        warn,
    )

    challenge = resolve_challenge(
        challenge_name=challenge_name,
        ctf_name=ctf,
        prompt="Select a challenge to scaffold:",
    )

    if plugin and category:
        error("--plugin and --category cannot be combined.")
        raise typer.Exit(code=1)

    if plugin:
        chosen_plugin = plugin_manager.get_plugin_by_name(plugin)
        if chosen_plugin is None:
            error(f"No plugin named '{plugin}'. See `pwnv plugin list`.")
            raise typer.Exit(code=1)
    else:
        if category:
            try:
                chosen_category = Category[category.lower()]
            except KeyError:
                choices = ", ".join(item.name for item in Category)
                error(f"Unknown category '{category}'. Choose one of: {choices}.")
                raise typer.Exit(code=1)
        else:
            chosen_category = prompt_category_selection(default=challenge.category)

        chosen_plugin = get_selected_plugin_for_category(chosen_category)
        if chosen_plugin is None:
            error(
                f"No plugin selected for category '{chosen_category.name}'. "
                "Use `pwnv plugin select` to choose one."
            )
            raise typer.Exit(code=1)

    challenge.path.mkdir(parents=True, exist_ok=True)

    with template_write_policy(force=force, suffix=suffix) as report:
        chosen_plugin.create_template(challenge)

    for path in report.written:
        success(f"wrote [cyan]{path.name}[/]")
    if report.skipped:
        names = ", ".join(path.name for path in report.skipped)
        warn(
            f"{names} already exists - left untouched. "
            "Use --force to overwrite, or --suffix to write alongside it."
        )

    try:
        chosen_plugin.logic(challenge)
    except Exception as exc:
        # A plugin run outside its own category can hit assumptions that do not
        # hold, e.g. a pwn plugin looking for a binary in a web challenge.
        warn(f"Plugin logic failed for {challenge.name}: {exc}")
        raise typer.Exit(code=1) from exc

    if not report.written and not report.skipped:
        info(f"{challenge.name} scaffolded, but the plugin wrote no templates.")
    else:
        success(f"[cyan]{challenge.name}[/] scaffolded.")


@app.command(name="path")
@config_exists()
@challenges_exists()
def path_(
    challenge_name: str | None = typer.Argument(
        None, help="Challenge name (fuzzy selection when omitted)"
    ),
    ctf: str | None = typer.Option(None, "--ctf", help="Limit selection to one CTF"),
) -> None:
    """
    Print a challenge directory and nothing else.

    Built for `cd "$(pwnv challenge path baby-rop)"`; see `pwnv shell-init` for
    the `pwncd` wrapper.
    """
    from pwnv.utils import prompt_on_tty, resolve_challenge

    with prompt_on_tty() as stdout:
        challenge = resolve_challenge(
            challenge_name=challenge_name,
            ctf_name=ctf,
            prompt="Select a challenge to enter:",
        )
        print(str(challenge.path), file=stdout)
