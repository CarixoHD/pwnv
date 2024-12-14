import typer
from pwnv.models import Challenge
from pwnv.models.challenge import Category, Solved
from pwnv.setup import Core
from pwnv.cli.utils import (
    config_exists,
    read_config,
    write_config,
    get_challenges,
    get_ctfs,
    is_duplicate,
    get_tags,
    set_tags,
    select_challenge,
    select_ctf,
    select,
    confirm,
    select_tags,
    get_current_ctf,
    get_current_challenge,
)
from pathlib import Path
from InquirerPy import inquirer
from typing import Annotated

from rich.table import Table
from rich import print
from rich.markup import escape
import shutil

app = typer.Typer(no_args_is_help=True)


@app.command()
@config_exists()
def add(name: str):
    ctfs = get_ctfs()
    if not ctfs:
        print("[red]:x: Error:[/] No CTFs found.")
        return

    challenges = get_challenges()
    ctf = get_current_ctf(ctfs)
    # if any(ctf.path == Path.cwd() or ctf.path in Path.cwd().parents for ctf in ctfs):
    #    ctf = next(ctf for ctf in ctfs if ctf.path == Path.cwd())
    if not ctf:
        running_ctfs = list(filter(lambda ctf: ctf.running, ctfs))
        if not running_ctfs:
            print("[red]:x: Error:[/] No running CTFs found.")
            return
        ctf = select_ctf(running_ctfs, "Select a CTF to add the challenge to:")

    path = ctf.path / name
    ctf_challenges = list(
        filter(lambda challenge: challenge.ctf_id == ctf.id, challenges)
    )
    if is_duplicate(name=name, model_list=ctf_challenges):
        print(f"[red]:x: Error:[/] Challenge with name {name} already exists.")
        return

    category = select(
        "Select the challenge category:",
        [category.name for category in Category],
    )

    # category = inquirer.select(
    #    "Select the challenge category:",
    #    choices=[category.name for category in Category],
    # ).execute()

    challenge = Challenge(
        ctf_id=ctf.id, name=name, path=path, category=Category[category]
    )
    challenges.append(challenge)

    config = read_config()
    config["challenges"] = [challenge.model_dump() for challenge in challenges]
    write_config(config)
    Path.mkdir(path, parents=True, exist_ok=True)
    Core(challenge)

    print(
        f"[green]:tada: Success![/] Added challenge [medium_spring_green]{name}[/] to CTF [medium_spring_green]{ctf.name}[/]."
    )


@app.command()
@config_exists()
def remove():
    ctfs = get_ctfs()
    challenges = get_challenges()
    if not challenges:
        print("[red]:x: Error:[/] No challenges found.")
        return

    ctf = get_current_ctf(ctfs)
    # if any(ctf.path == Path.cwd() or ctf.path in Path.cwd().parents for ctf in ctfs):
    #    ctf = next(ctf for ctf in ctfs if ctf.path == Path.cwd())
    if not ctf:
        ctfs_with_challenges = list(
            filter(
                lambda ctf: any(challenge.ctf_id == ctf.id for challenge in challenges),
                ctfs,
            )
        )

        ctf = select_ctf(
            ctfs_with_challenges, "Select a CTF to remove the challenge from:"
        )

    ctf_challenges = list(
        filter(lambda challenge: challenge.ctf_id == ctf.id, challenges)
    )
    if not ctf_challenges:
        print("[red]:x: Error:[/] No challenges found.")
        return

    challenge = select_challenge(ctf_challenges, "Select a challenge to remove:")

    if any(challenge.path.iterdir()):
        if not confirm(
            "Challenge directory is not empty. Are you sure you want to remove it?",
            False,
        ):
            # if not inquirer.confirm(
            #    "Challenge directory is not empty. Are you sure you want to remove it?",
            #    default=False,
            # ).execute():
            return

    challenges.remove(challenge)

    config = read_config()
    config["challenges"] = [challenge.model_dump() for challenge in challenges]
    write_config(config)
    shutil.rmtree(challenge.path)

    print(
        f"[green]:tada: Success![/] Removed challenge [medium_spring_green]{challenge.name}[/] from CTF [medium_spring_green]{ctf.name}[/]."
    )


@app.command()
@config_exists()
def info(
    all: Annotated[bool, typer.Option(help="List all challenges")] = False,
):
    challenges = get_challenges()

    current_ctf = get_current_ctf(get_ctfs())

    if not challenges:
        print("[bold red]:x: Error:[/] No challenges found.")
        return

    current_challenge = get_current_challenge(challenges)
    if current_challenge and not all:
        show_challenge(current_challenge)
        return

    if current_ctf and not all:
        challenges = list(
            filter(lambda challenge: challenge.ctf_id == current_ctf.id, challenges)
        )

    while True:
        challenge = select_challenge(challenges, "Select a challenge to view:")
        show_challenge(challenge)
        input("Press Enter to continue...")


@app.command(name="filter")
@config_exists()
def filter_():
    challenges = get_challenges()
    solved_challenges = list(
        filter(lambda challenge: challenge.solved == Solved.solved, challenges)
    )
    if not solved_challenges:
        print("[bold red]:x: Error:[/] No solved challenges found.")
        return

    # chosen_tags = select_tags("Select tags to filter by:")
    # filtered_challenges = list(filter(lambda challenge: any(tag in challenge.tags for tag in chosen_tags), solved_challenges))

    # if not filtered_challenges:
    #    print("[bold red]:x: Error:[/] No challenges found.")
    #    return
    while True:
        chosen_tags = select_tags("Select tags to filter by:")
        filtered_challenges = list(
            filter(
                lambda challenge: any(tag in challenge.tags for tag in chosen_tags),
                solved_challenges,
            )
        )

        if not filtered_challenges:
            print("[bold red]:x: Error:[/] No challenges found.")
        challenge = select_challenge(filtered_challenges, "Select a challenge to view:")
        show_challenge(challenge)
        input("Press Enter to continue...")


@app.command()
@config_exists()
def solve(
    no_tags: Annotated[
        bool, typer.Option(help="Do not add tags to the challenge")
    ] = False,
    no_flag: Annotated[
        bool, typer.Option(help="Do not add a flag to the challenge")
    ] = False,
):
    challenges = get_challenges()

    unsolved_challenges = list(
        filter(lambda challenge: challenge.solved == Solved.unsolved, challenges)
    )
    if not unsolved_challenges:
        print("[bold red]:x: Error:[/] No unsolved challenges found.")
        return

    current_challenge = get_current_challenge(challenges)
    if current_challenge:
        challenge = current_challenge
    else:
        challenge = select_challenge(
            unsolved_challenges, "Select a challenge to mark as solved:"
        )
    if not confirm(
        f"Are you sure you want to mark challenge {challenge.name} as solved?", True
    ):
        return
    index = challenges.index(challenge)
    challenge.solved = Solved.solved
    tags = get_tags()
    """
    chosen_tags = inquirer.fuzzy(
        message="Select tags for the challenge (tab to toggle):",
        choices=set(tags),
        multiselect=True,
        border=True,
        mandatory=False,
    ).execute()
    """
    if not no_tags:
        while not (
            raw_tags := inquirer.text(
                message="Enter tags for the challenge (comma separated):"
            ).execute()
        ):
            print("[red]:x: Error:[/] Tags cannot be empty.")

        chosen_tags = [item.strip() for item in raw_tags.split(",")] if raw_tags else []

        tags.extend(chosen_tags)

        set_tags(list(set(tags)))
        challenge.tags = list(set(chosen_tags))
    if not no_flag:
        while not (
            flag := inquirer.text(message="Enter the flag for the challenge:").execute()
        ):
            print("[red]:x: Error:[/] Flag cannot be empty.")

        challenge.flag = flag

    config = read_config()
    config["challenges"][index] = challenge.model_dump()
    write_config(config)


# def select_challenge(challenges: List[Challenge], msg: str) -> Challenge:
#    challenge = fuzzy_select(
#        choices=get_challenge_choices(challenges), message=msg, transformer=lambda result: result.split(" ")[0]
#    )
#    return challenge


def show_challenge(challenge: Challenge):
    # print challenge info as toml format
    # print name of challenge as light purple in format [name]
    print(f"[blue]{escape("["+challenge.name+"]")}[/]")   
    print(f"[red]ctf[/] = '{list(filter(lambda ctf: ctf.id == challenge.ctf_id, get_ctfs()))[0].name}'")
    print(f"[red]category[/] = '{challenge.category.name}'")
    print(f"[red]path[/] = '{str(challenge.path)}'")
    print(f"[red]solved[/] = '{str(challenge.solved.name)}'")
    print(f"[red]points[/] = '{str(challenge.points)}'")
    print(f"[red]flag[/] = '{str(challenge.flag)}'")
    print(f"[red]tags[/] = '{', '.join(challenge.tags) if challenge.tags else ''}'")
    return
    
    
    table = Table(title="Challenge info")

    table.add_column("Name", style="cyan")
    table.add_column("CTF", style="magenta")
    table.add_column("Category", style="magenta")
    table.add_column("Path", style="green")
    table.add_column("Solved", style="yellow")
    table.add_column("Points", style="blue")
    table.add_column("Flag", style="blue")
    table.add_column("Tags", style="blue")

    table.add_row(
        challenge.name,
        list(filter(lambda ctf: ctf.id == challenge.ctf_id, get_ctfs()))[0].name,
        challenge.category.name,
        str(challenge.path),
        str(challenge.solved.name),
        str(challenge.points),
        str(challenge.flag),
        ", ".join(challenge.tags) if challenge.tags else "None",
    )

    print(table)
