import typer
from pwnv.models import Challenge
from pwnv.models.challenge import Category
from pwnv.cli.utils import (
    config_exists,
    read_config,
    write_config,
    get_challenges,
    get_ctfs,
    select_fuzzy,
    is_duplicate,
)
from pathlib import Path
import uuid
from typing import List

from InquirerPy import inquirer
from pwnv.setup import Core

from rich.table import Table


from rich import print

app = typer.Typer(no_args_is_help=True)


@app.command()
@config_exists()
def add(name: str):
    ctfs = get_ctfs()
    if not ctfs:
        print("[red]:x: Error:[/] No CTFs found.")
        return
    ctf_challenges = get_challenges()

    if _is_in_ctf_directory(ctfs):
        ctf = _get_current_ctf(ctfs)
    else:
        running_ctfs = list(filter(lambda ctf: ctf.running, ctfs))
        ctf = select_fuzzy(running_ctfs, "Select a CTF to add the challenge to:")

    ctf_challenges = list(
        filter(lambda challenge: challenge.ctf_id == ctf.id, ctf_challenges)
    )
    if is_duplicate(name, None, ctf_challenges):
        print(f"[red]:x: Error:[/] Challenge with name {name} already exists.")
        return
    
    category = inquirer.select("Select the challenge category:", choices=[category.name for category in Category]).execute()
    _add_challenge_to_config(name, ctf.id, Path.cwd() / name, ctf_challenges, Category[category])
    print(
        f"[green]:tada: Success![/] Added challenge [medium_spring_green]{name}[/] to CTF [medium_spring_green]{ctf.name}[/]."
    )


@app.command(name="list")
@config_exists()
def list_():
    challenges = get_challenges()

    if not challenges:
        print("[bold red]:x: Error:[/] No challenges found.")
        return

    challenge = select_fuzzy(challenges, "Challenges:")
    
    table = Table(title="Challenge info")
    
    table.add_column("Name", style="cyan")
    table.add_column("Category", style="magenta")
    table.add_column("Path", style="green")
    table.add_column("Solved", style="yellow")
    table.add_column("Points", style="blue")
    table.add_column("Flag", style="blue")
    table.add_column("Tags", style="blue")
    
    table.add_row(
        challenge.name,
        challenge.category.name,
        str(challenge.path),
        str(challenge.solved.name),
        str(challenge.points),
        str(challenge.flag),
        str(challenge.tags),
    )
    
    print(table)

@app.command()
@config_exists()
def remove():
    ...


def _is_in_ctf_directory(ctfs: List[Challenge]) -> bool:
    return any(ctf.path == Path.cwd() or ctf.path in Path.cwd().parents for ctf in ctfs)


def _get_current_ctf(ctfs: List[Challenge]):
    return next(ctf for ctf in ctfs if ctf.path == Path.cwd())


def _add_challenge_to_config(
    name: str, ctf_id: uuid.UUID, path: Path, challenges: List[Challenge], category: Category
):
    challenge = Challenge(ctf_id=ctf_id, name=name, path=path, category=category)
    challenges.append(challenge)

    config = read_config()
    config["challenges"] = [challenge.model_dump() for challenge in challenges]
    write_config(config)
    Path.mkdir(path)
    Core(challenge)
