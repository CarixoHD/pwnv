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
    select_fuzzy,
    is_duplicate,
    get_tags,
    set_tags,
)
from pathlib import Path
from typing import List
from InquirerPy import inquirer, prompt
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
    
    challenges = get_challenges()

    if any(ctf.path == Path.cwd() or ctf.path in Path.cwd().parents for ctf in ctfs):
        ctf = next(ctf for ctf in ctfs if ctf.path == Path.cwd())
    else:
        running_ctfs = list(filter(lambda ctf: ctf.running, ctfs))
        ctf = select_fuzzy(running_ctfs, "Select a CTF to add the challenge to:")

    path = ctf.path / name
    ctf_challenges = list(
        filter(lambda challenge: challenge.ctf_id == ctf.id, challenges)
    )
    if is_duplicate(name=name, model_list=ctf_challenges):
        print(f"[red]:x: Error:[/] Challenge with name {name} already exists.")
        return
    
    category = inquirer.select("Select the challenge category:", choices=[category.name for category in Category]).execute()

    challenge = Challenge(ctf_id=ctf.id, name=name, path=path, category=Category[category])
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
    ...

@app.command(name="list")
@config_exists()
def list_():
    challenges = get_challenges()

    if not challenges:
        print("[bold red]:x: Error:[/] No challenges found.")
        return

    challenge = list_challenges(challenges)
    
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
        ", ".join(challenge.tags) if challenge.tags else "None",
    )
    
    print(table)
    return challenge


@app.command()
@config_exists()
def solve():
    challenges = get_challenges()
    unsolved_challenges = list(filter(lambda challenge: challenge.solved == Solved.unsolved, challenges))
    if not unsolved_challenges:
        print("[bold red]:x: Error:[/] No unsolved challenges found.")
        return
    
    challenge = list_challenges(unsolved_challenges)
    index = challenges.index(challenge)
    challenge.solved = Solved.solved
    tags = get_tags()
    '''
    chosen_tags = inquirer.fuzzy(
        message="Select tags for the challenge (tab to toggle):",
        choices=set(tags),
        multiselect=True,
        border=True,
        mandatory=False,
    ).execute()
    '''
    while not (raw_tags := inquirer.text(message="Enter tags for the challenge (comma separated):").execute()):
        print("[red]:x: Error:[/] Tags cannot be empty.")
        
    chosen_tags = [item.strip() for item in raw_tags.split(",")] if raw_tags else []

    tags.extend(chosen_tags)
    
    set_tags(list(set(tags)))
    challenge.tags = list(set(chosen_tags))
        
    config = read_config()
    config["challenges"][index] = challenge.model_dump()
    write_config(config)
    
    
    
    
def list_challenges(challenges: List[Challenge]) -> Challenge:
    return select_fuzzy(challenges, "Challenges:")