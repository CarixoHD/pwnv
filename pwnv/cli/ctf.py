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
def add(
    name: str,
    local: bool = typer.Option(
        False, "--local", help="Create a local CTF without prompting"
    ),
    url: str | None = typer.Option(
        None, "--url", help="Remote CTF URL (skips the remote prompt)"
    ),
    username: str | None = typer.Option(None, "--username", envvar="PWNV_CTF_USERNAME"),
    password: str | None = typer.Option(
        None, "--password", envvar="PWNV_CTF_PASSWORD", hide_input=True
    ),
    token: str | None = typer.Option(
        None, "--token", envvar="PWNV_CTF_TOKEN", hide_input=True
    ),
) -> None:
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

    credentials = {"username": username, "password": password, "token": token}
    if local:
        if url:
            error("--local cannot be combined with --url.")
            raise typer.Exit(code=1)
        credentials = {"username": None, "password": None, "token": None}

    has_credentials = any(credentials.values())
    if has_credentials and not url:
        error("--url is required when credentials are provided.")
        raise typer.Exit(code=1)
    if bool(username) != bool(password):
        error("--username and --password must be provided together.")
        raise typer.Exit(code=1)
    if token and username:
        error("Use either token or username/password authentication, not both.")
        raise typer.Exit(code=1)

    remote = bool(url) or (
        not local
        and prompt_confirm(
            "Do you want to add a remote CTF? (y/n)",
            default=False,
        )
    )
    if remote:
        if not add_remote_ctf(
            CTF(name=name, path=path, url=url or prompt_text("Enter the URL:")),
            credentials if has_credentials else None,
        ):
            return
    else:
        add_ctf(CTF(name=name, path=path))

    success(f"CTF [cyan]{name}[/] added.")


@app.command()
@config_exists()
@ctfs_exists()
def remove(
    ctf: str | None = typer.Option(None, "--ctf", help="CTF name (skips selection)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt"),
) -> None:
    """Removes an existing CTF and all its associated challenges."""
    from pwnv.utils import (
        error,
        get_ctf_by_name,
        get_ctfs,
        prompt_confirm,
        prompt_ctf_selection,
        remove_ctf,
        success,
    )

    chosen_ctf = get_ctf_by_name(ctf) if ctf else None
    if ctf and chosen_ctf is None:
        error(f"CTF '{ctf}' does not exist.")
        raise typer.Exit(code=1)
    chosen_ctf = chosen_ctf or prompt_ctf_selection(
        get_ctfs(), "Select a CTF to remove:"
    )
    if not yes and not prompt_confirm(
        f"Remove CTF '{chosen_ctf.name}' and all its challenges?",
        default=False,
    ):
        return
    remove_ctf(chosen_ctf)
    success(f"CTF [cyan]{chosen_ctf.name}[/] removed")


@app.command(name="info")
@config_exists()
@ctfs_exists()
def info_(
    ctf: str | None = typer.Option(None, "--ctf", help="CTF name (skips selection)"),
) -> None:
    """Displays detailed information about a selected CTF."""
    from pwnv.utils import (
        error,
        get_ctf_by_name,
        get_ctfs,
        prompt_confirm,
        prompt_ctf_selection,
        show_ctf,
    )

    if ctf:
        chosen_ctf = get_ctf_by_name(ctf)
        if chosen_ctf is None:
            error(f"CTF '{ctf}' does not exist.")
            raise typer.Exit(code=1)
        show_ctf(chosen_ctf)
        return

    while True:
        ctfs: list[CTF] = get_ctfs()
        show_ctf(prompt_ctf_selection(ctfs, "Select a CTF to show info:"))
        if not prompt_confirm("Show another CTF?", default=False):
            break


@app.command()
@config_exists()
@ctfs_exists()
def stop(
    ctf: str | None = typer.Option(None, "--ctf", help="CTF name (skips selection)"),
) -> None:
    """Marks a running CTF as stopped."""
    from pwnv.models.ctf import Status
    from pwnv.utils import (
        error,
        get_ctf_by_name,
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
    named_ctf = get_ctf_by_name(ctf) if ctf else None
    if ctf and named_ctf is None:
        error(f"CTF '{ctf}' does not exist.")
        raise typer.Exit(code=1)
    if named_ctf and named_ctf not in running:
        warn(f"CTF '{ctf}' is already stopped.")
        return
    current = named_ctf or get_current_ctf()
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
def start(
    ctf: str | None = typer.Option(None, "--ctf", help="CTF name (skips selection)"),
) -> None:
    """Marks a stopped CTF as running."""
    from pwnv.models.ctf import Status
    from pwnv.utils import (
        error,
        get_ctf_by_name,
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
    named_ctf = get_ctf_by_name(ctf) if ctf else None
    if ctf and named_ctf is None:
        error(f"CTF '{ctf}' does not exist.")
        raise typer.Exit(code=1)
    if named_ctf and named_ctf not in stopped:
        warn(f"CTF '{ctf}' is already running.")
        return
    current = named_ctf or get_current_ctf()
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
def sync(
    ctf: str | None = typer.Option(None, "--ctf", help="CTF name (skips selection)"),
    watch: bool = typer.Option(
        False, "--watch", "-w", help="Keep polling for changes until you stop it"
    ),
    interval: int = typer.Option(
        60, "--interval", min=10, help="Seconds between polls in --watch mode"
    ),
    refresh_attachments: bool = typer.Option(
        False,
        "--refresh-attachments",
        help="Re-download attachments even when the local copies still match",
    ),
) -> None:
    """Synchronizes challenges for a remote CTF."""
    from pwnv.utils import (
        error,
        get_ctf_by_name,
        get_ctfs,
        get_current_ctf,
        prompt_ctf_selection,
        render_sync_summary,
        success,
        sync_remote_ctf,
        warn,
    )

    ctfs = get_ctfs()
    if not ctfs:
        warn("No CTFs found.")
        return

    chosen_ctf = get_ctf_by_name(ctf) if ctf else None
    if ctf and chosen_ctf is None:
        error(f"CTF '{ctf}' does not exist.")
        raise typer.Exit(code=1)
    chosen_ctf = (
        chosen_ctf
        or get_current_ctf()
        or prompt_ctf_selection(ctfs, "Select a CTF to sync:")
    )
    if not chosen_ctf.url:
        warn("Selected CTF has no remote URL.")
        return

    if not watch:
        summary = sync_remote_ctf(
            chosen_ctf, refresh_attachments=refresh_attachments, report=False
        )
        if summary is None:
            raise typer.Exit(code=1)
        render_sync_summary(chosen_ctf.name, summary)
        success(f"CTF [cyan]{chosen_ctf.name}[/] synced.")
        return

    _watch(chosen_ctf, interval=interval, refresh_attachments=refresh_attachments)


_MAX_WATCH_INTERVAL = 15 * 60


def _watch(ctf: CTF, *, interval: int, refresh_attachments: bool) -> None:
    """Poll ``ctf`` until it stops running or the user interrupts."""
    import time

    from pwnv.utils import (
        get_ctf_by_name,
        info,
        render_sync_summary,
        sync_remote_ctf,
        warn,
    )

    info(f"Watching [cyan]{ctf.name}[/] every {interval}s. Press Ctrl-C to stop.")
    delay = interval
    try:
        while True:
            summary = sync_remote_ctf(
                ctf, refresh_attachments=refresh_attachments, report=False
            )
            refresh_attachments = False

            if summary is None:
                delay = min(delay * 2, _MAX_WATCH_INTERVAL)
                warn(f"Sync failed. Retrying in {delay}s.")
            else:
                delay = interval
                render_sync_summary(ctf.name, summary, quiet=True)

            time.sleep(delay)

            current = get_ctf_by_name(ctf.name)
            if current is None or not current.running:
                info(f"{ctf.name} is no longer running - stopping the watch.")
                return
            ctf = current
    except KeyboardInterrupt:
        info("Stopped watching.")
