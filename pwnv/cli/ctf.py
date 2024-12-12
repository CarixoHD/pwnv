import typer
from typing import Annotated, List
from pwnv.models import CTF
from pwnv.models.ctf import Status
from pathlib import Path

from rich import print
from rich.table import Table

from pwnv.cli.utils import (
    config_exists,
    get_ctfs,
    read_config,
    write_config,
    select_fuzzy,
    is_duplicate,
    get_challenges,
)


app = typer.Typer(no_args_is_help=True)


@app.command()
@config_exists()
def add(name: str, path: Annotated[Path, "Path to the CTF directory"] = Path.cwd()):
    ctfs = get_ctfs()
    if any(ctf.path == Path.cwd() or ctf.path in Path.cwd().parents for ctf in ctfs):
        print("[red]:x: Error:[/] You cannot create a CTF in a CTF directory.")
        return

    path = path / name
    if is_duplicate(None, path, ctfs):
        print(f"[red]:x: Error:[/] CTF with name {name} or path {path} already exists.")
        return

    path.mkdir(parents=True, exist_ok=True)

    _add_ctf_to_config(name, path, ctfs)
    print(
        f"[green]:tada: Success![/] Added CTF [medium_spring_green]{name}[/] at [medium_spring_green]{path}[/]."
    )


@app.command()
def remove():
    ctfs = get_ctfs()
    if not ctfs:
        print("[red]:x: Error:[/] No CTFs found.")
        return

    chosen_ctf = select_fuzzy(ctfs, "Select a CTF to remove:")
    confirm = typer.confirm(
        f"Are you sure you want to remove CTF {chosen_ctf.name}?", default=False
    )
    if not confirm:
        return

    ctfs.remove(chosen_ctf)

    Path.rmdir(chosen_ctf.path)

    _write_ctfs_to_config(ctfs)
    print(
        f"[green]:tada: Success![/] Removed CTF [medium_spring_green]{chosen_ctf.name}[/]."
    )


@app.command(name="list")
def list_():
    ctfs = get_ctfs()
    if not ctfs:
        print("[red]:x: Error:[/] No CTFs found.")
        return

    ctf = select_fuzzy(ctfs, "CTFs:")
    table = Table(title="CTF Details")
    table.add_column("Name", style="cyan")
    table.add_column("Path", style="magenta")
    table.add_column("Running", style="green")
    table.add_column("Year", style="yellow")
    table.add_column("Number of Challenges", style="blue")

    table.add_row(
        ctf.name,
        str(ctf.path),
        str(ctf.running),
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


@app.command()
def stop():
    current_path = Path.cwd()
    ctfs = get_ctfs()
    running_ctfs = list(filter(lambda ctf: ctf.running, ctfs))
    if not running_ctfs:
        print("[red]:x: Error:[/] No CTFs found.")
        return

    for ctf in running_ctfs:
        if current_path == ctf.path or current_path in ctf.path.parents:
            chosen_ctf = ctf
            break
    else:
        chosen_ctf = select_fuzzy(running_ctfs, "Select a CTF to stop:")

    index = ctfs.index(chosen_ctf)
    chosen_ctf.running = Status.stopped
    ctfs[index] = chosen_ctf

    _write_ctfs_to_config(ctfs)
    print(
        f"[green]:tada: Success![/] Stopped CTF [medium_spring_green]{chosen_ctf.name}[/]."
    )


@app.command()
def start():
    current_path = Path.cwd()
    ctfs = get_ctfs()
    stopped_ctfs = list(filter(lambda ctf: not ctf.running, ctfs))
    if not stopped_ctfs:
        print("[red]:x: Error:[/] No stopped CTFs found.")
        return

    for ctf in stopped_ctfs:
        if current_path == ctf.path or current_path in ctf.path.parents:
            chosen_ctf = ctf
            break
    else:
        chosen_ctf = select_fuzzy(stopped_ctfs, "Select a CTF to start:")

    index = ctfs.index(chosen_ctf)
    chosen_ctf.running = Status.running
    ctfs[index] = chosen_ctf

    _write_ctfs_to_config(ctfs)
    print(
        f"[green]:tada: Success![/] Started CTF [medium_spring_green]{chosen_ctf.name}[/]."
    )


def _add_ctf_to_config(name: str, path: Path, ctfs: List[CTF]):
    ctf = CTF(name=name, path=path)
    ctfs.append(ctf)
    _write_ctfs_to_config(ctfs)


def _write_ctfs_to_config(ctfs: List[CTF]):
    config = read_config()
    config["ctfs"] = [ctf.model_dump() for ctf in ctfs]
    write_config(config)
