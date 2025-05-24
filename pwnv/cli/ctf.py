from pathlib import Path

import typer

from pwnv.cli.utils import (
    add_ctf,
    add_remote_ctf,
    config_exists,
    ctfs_exists,
    error,
    get_ctfs,
    get_ctfs_path,
    get_current_ctf,
    get_running_ctfs,
    get_stopped_ctfs,
    is_duplicate,
    prompt_confirm,
    prompt_ctf_selection,
    prompt_text,
    remove_ctf,
    sanitize,
    show_ctf,
    success,
    update_ctf,
    warn,
)
from pwnv.models import CTF
from pwnv.models.ctf import Status

app = typer.Typer(no_args_is_help=True)


@app.command()
@config_exists()
def add(name: str):
    path: Path = (get_ctfs_path() / sanitize(name)).resolve()
    if is_duplicate(path=path, model_list=get_ctfs()):
        error(f"CTF [cyan]{name}[/] already exists.")

        return

    if prompt_confirm(
        "Do you want to add a remote CTF? (y/n)",
        default=False,
    ):
        add_remote_ctf(CTF(name=name, path=path, url=prompt_text("Enter the URL:")))
    else:
        add_ctf(CTF(name=name, path=path))
    success(f"CTF [cyan]{name}[/] added.")


@app.command()
@config_exists()
@ctfs_exists()
def remove():
    chosen_ctf = prompt_ctf_selection(get_ctfs(), "Select a CTF to remove:")
    if not prompt_confirm(
        f"Remove CTF '{chosen_ctf.name}' and all its challenges?",
        default=False,
    ):
        return
    remove_ctf(chosen_ctf)
    success(f"CTF [cyan]{chosen_ctf.name}[/] removed")


@app.command()
@config_exists()
@ctfs_exists()
def info():
    while True:
        ctfs: list[CTF] = get_ctfs()
        show_ctf(prompt_ctf_selection(ctfs, "Select a CTF to show info:"))
        if not prompt_confirm("Show another CTF?", default=False):
            break


@app.command()
@config_exists()
@ctfs_exists()
def stop():
    running: list[CTF] = get_running_ctfs()
    if not running:
        warn("No running CTFs found.")

        return
    current = get_current_ctf()
    if current in running:
        chosen_ctf = current
    else:
        chosen_ctf = prompt_ctf_selection(running, "Select a CTF to stop:")
    chosen_ctf.running = Status.stopped
    update_ctf(chosen_ctf)
    success(f"CTF [cyan]{chosen_ctf.name}[/] stopped.")


@app.command()
@config_exists()
@ctfs_exists()
def start():
    stopped: list[CTF] = get_stopped_ctfs()
    if not stopped:
        warn("No stopped CTFs found.")

        return
    current = get_current_ctf()
    if current in stopped:
        chosen_ctf = current
    else:
        chosen_ctf = prompt_ctf_selection(stopped, "Select a CTF to start:")
    chosen_ctf.running = Status.running
    update_ctf(chosen_ctf)
    success(f"CTF [cyan]{chosen_ctf.name}[/] started.")
