import typer
from typing import Annotated, Optional
from pwnv.models import CTF
from pwnv.models.ctf import Status
from pathlib import Path
import shutil
from rich import print
from rich.table import Table
from rich.markup import escape
from pwnv.cli.utils import (
    config_exists,
    get_ctfs,
    read_config,
    write_config,
    is_duplicate,
    get_challenges,
    get_current_ctf,
    select_ctf,
    confirm,
    get_env_path,
    is_default_ctf_path,
)


app = typer.Typer(no_args_is_help=True)


@app.command()
@config_exists()
def add(
    name: str,
    path: Annotated[
        Optional[Path],
        typer.Option(
            help="Path to the CTF directory",
        ),
    ] = Path.cwd(),
):
    if is_default_ctf_path():
        path = get_env_path().parent
    ctfs = get_ctfs()
    if get_current_ctf(ctfs) and (path in Path.cwd().parents or path == Path.cwd()):
        print("[red]:x: Error:[/] You cannot create a CTF in a CTF directory.")
        return
    # if any(ctf.path == Path.cwd() or ctf.path in Path.cwd().parents for ctf in ctfs):
    #    print("[red]:x: Error:[/] You cannot create a CTF in a CTF directory.")
    #    return

    path = (path / name).resolve()
    if is_duplicate(path=path, model_list=ctfs):
        print(f"[red]:x: Error:[/] CTF with name {name} or path {path} already exists.")
        return

    ctf = CTF(name=name, path=path)
    ctfs.append(ctf)
    config = read_config()
    config["ctfs"] = [ctf.model_dump() for ctf in ctfs]
    write_config(config)
    path.mkdir(parents=True, exist_ok=True)
    print(
        f"[green]:tada: Success![/] Added CTF [medium_spring_green]{name}[/] at [medium_spring_green]{path}[/]."
    )


@app.command()
def remove():
    ctfs = get_ctfs()
    if not ctfs:
        print("[red]:x: Error:[/] No CTFs found.")
        return

    # ctf = get_current_ctf(ctfs)

    #########################################
    # if ctf:
    #    print("[red]:x: Error:[/] You cannot remove a CTF in a CTF directory.")
    #    return
    #########################################
    chosen_ctf = select_ctf(ctfs, "Select a CTF to remove:")
    if not confirm(
        f"Are you sure you want to remove CTF {chosen_ctf.name} and all its challenges?",
        default=False,
    ):
        return
    # confirm = typer.confirm(
    #    f"Are you sure you want to remove CTF {chosen_ctf.name}?", default=False
    # )
    # if not confirm:
    #    return
    challenges = get_challenges()
    challenges = list(
        filter(lambda challenge: challenge.ctf_id != chosen_ctf.id, challenges)
    )

    ctfs.remove(chosen_ctf)

    shutil.rmtree(chosen_ctf.path)

    config = read_config()
    config["ctfs"] = [ctf.model_dump() for ctf in ctfs]
    config["challenges"] = [challenge.model_dump() for challenge in challenges]
    write_config(config)

    print(
        f"[green]:tada: Success![/] Removed CTF [medium_spring_green]{chosen_ctf.name}[/]."
    )


@app.command()
def info():
    ctfs = get_ctfs()
    if not ctfs:
        print("[red]:x: Error:[/] No CTFs found.")
        return

    while True:
        ctf = select_ctf(ctfs, "Select a CTF to view:")
        show_ctf(ctf)
        input("Press Enter to continue...")


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
        chosen_ctf = select_ctf(running_ctfs, "Select a CTF to stop:")

    index = ctfs.index(chosen_ctf)
    chosen_ctf.running = Status.stopped
    ctfs[index] = chosen_ctf

    config = read_config()
    config["ctfs"] = [ctf.model_dump() for ctf in ctfs]
    write_config(config)
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
        chosen_ctf = select_ctf(stopped_ctfs, "Select a CTF to start:")
        # chosen_ctf = select_fuzzy(stopped_ctfs, "Select a CTF to start:")

    index = ctfs.index(chosen_ctf)
    chosen_ctf.running = Status.running
    ctfs[index] = chosen_ctf

    config = read_config()
    config["ctfs"] = [ctf.model_dump() for ctf in ctfs]
    write_config(config)

    print(
        f"[green]:tada: Success![/] Started CTF [medium_spring_green]{chosen_ctf.name}[/]."
    )


def show_ctf(ctf: CTF):
    print(f"[blue]{escape("["+ctf.name+"]")}[/]")
    print(f"[red]path[/] = '{str(ctf.path)}'")
    print(f"[red]running[/] = '{str(ctf.running.name)}'")
    print(f"[red]date[/] = '{str(ctf.created_at.date())}'")
    print(
        f"[red]num_challenges[/] = {str(len(list(filter(lambda challenge: challenge.ctf_id == ctf.id, get_challenges()))))}"
    )
    return

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
