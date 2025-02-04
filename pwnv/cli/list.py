import typer
from typing import Annotated, Optional
from pwnv.models import CTF, Challenge
from rich import print
from rich.table import Table

from pwnv.cli.utils import (
    config_exists,
    get_ctfs,
    get_challenges,
)

# CURRENTLY NOT IN USE

app = typer.Typer(no_args_is_help=True)


@app.command(name="list")
@config_exists()
def list_(
    all: Annotated[
        Optional[bool], typer.Option(help="List all CTFs and challenges")
    ] = False,
):
    print(":warning: [red]This command is not implemented yet.[/] :warning:")


def show_challenge(challenge: Challenge):
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


def show_ctf(ctf: CTF):
    table = Table(title="CTF Details")
    table.add_column("Name", style="cyan")
    table.add_column("Path", style="magenta")
    table.add_column("Running", style="green")
    table.add_column("Year", style="yellow")
    table.add_column("Number of Challenges", style="blue")

    table.add_row(
        ctf.name,
        str(ctf.path),
        str("Running" if ctf.running else "Stopped"),
        str(ctf.created_at.year),
        str(
            len(
                list(
                    filter(
                        lambda challenge: challenge.ctf_id == ctf.id, get_challenges()
                    )
                )
            )
        ),
    )

    print(table)
