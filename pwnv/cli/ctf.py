from pathlib import Path

import typer

from pwnv.models import CTF
from pwnv.utils import (
    config_exists,
    ctfs_exists,
)

app = typer.Typer(no_args_is_help=True, help="Manage CTFs.")


@app.command()
@config_exists()
def add(name: str) -> None:
    """Adds a new CTF, either local or remote, to your environment."""
    from pwnv.utils import (
        add_ctf,
        add_remote_ctf,
        error,
        get_ctfs,
        get_ctfs_path,
        is_duplicate,
        prompt_confirm,
        prompt_text,
        sanitize,
        success,
    )

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
def remove() -> None:
    """Removes an existing CTF and all its associated challenges."""
    from pwnv.utils import (
        get_ctfs,
        prompt_confirm,
        prompt_ctf_selection,
        remove_ctf,
        success,
    )

    chosen_ctf = prompt_ctf_selection(get_ctfs(), "Select a CTF to remove:")
    if not prompt_confirm(
        f"Remove CTF '{chosen_ctf.name}' and all its challenges?",
        default=False,
    ):
        return
    remove_ctf(chosen_ctf)
    success(f"CTF [cyan]{chosen_ctf.name}[/] removed")


@app.command(name="info")
@config_exists()
@ctfs_exists()
def info_() -> None:
    """Displays detailed information about a selected CTF."""
    from pwnv.utils import (
        get_ctfs,
        prompt_confirm,
        prompt_ctf_selection,
        show_ctf,
    )

    while True:
        ctfs: list[CTF] = get_ctfs()
        show_ctf(prompt_ctf_selection(ctfs, "Select a CTF to show info:"))
        if not prompt_confirm("Show another CTF?", default=False):
            break


@app.command()
@config_exists()
@ctfs_exists()
def stop() -> None:
    """Marks a running CTF as stopped."""
    from pwnv.models.ctf import Status
    from pwnv.utils import (
        get_current_ctf,
        get_running_ctfs,
        prompt_ctf_selection,
        success,
        update_ctf,
        warn,
    )

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
def start() -> None:
    """Marks a stopped CTF as running."""
    from pwnv.models.ctf import Status
    from pwnv.utils import (
        get_current_ctf,
        get_stopped_ctfs,
        prompt_ctf_selection,
        success,
        update_ctf,
        warn,
    )

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


@app.command()
@config_exists()
@ctfs_exists()
def sync() -> None:
    """Synchronizes challenges for a remote CTF."""
    from pwnv.utils import (
        get_ctfs,
        get_current_ctf,
        prompt_ctf_selection,
        success,
        sync_remote_ctf,
        warn,
    )

    ctfs = get_ctfs()
    if not ctfs:
        warn("No CTFs found.")
        return

    chosen_ctf = get_current_ctf() or prompt_ctf_selection(
        ctfs, "Select a CTF to sync:"
    )
    if not chosen_ctf.url:
        warn("Selected CTF has no remote URL.")
        return

    sync_remote_ctf(chosen_ctf)
    success(f"CTF [cyan]{chosen_ctf.name}[/] synced.")
