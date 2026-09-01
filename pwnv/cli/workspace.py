import tarfile
from pathlib import Path

import typer

from pwnv.utils import config_exists

app = typer.Typer(no_args_is_help=True, help="Back up and transfer workspaces.")


def _confirm_replace(replace: bool, force: bool) -> None:
    """Ask before discarding metadata, unless there is none or --force was given."""
    from pwnv.utils import get_challenges, get_ctfs, prompt_confirm

    if not replace or force or not (get_ctfs() or get_challenges()):
        return
    if not prompt_confirm(
        "Discard the current workspace metadata and replace it?", default=False
    ):
        raise typer.Abort()


def _report_merge(summary: dict[str, int], *, replace: bool) -> None:
    """Say what the merge did with the records it was handed."""
    from pwnv.utils import info

    if replace:
        info(
            f"Metadata replaced with {summary['ctfs_added']} CTFs and "
            f"{summary['challenges_added']} challenges."
        )
        return
    info(
        f"Added {summary['ctfs_added']} CTFs and "
        f"{summary['challenges_added']} challenges; "
        f"skipped {summary['ctfs_skipped']} CTFs and "
        f"{summary['challenges_skipped']} already present."
    )


@app.command()
@config_exists()
def backup(
    destination: Path = typer.Argument(Path("pwnv-backup")),
    force: bool = typer.Option(False, "--force", "-f"),
) -> None:
    """Create a full archive, including challenge files and credentials."""
    from pwnv.utils import backup_workspace, error, success

    target = (
        destination
        if str(destination).endswith(".tar.gz")
        else Path(str(destination) + ".tar.gz")
    )
    if target.expanduser().exists() and not force:
        error(f"Backup already exists at {target}. Use --force to overwrite it.")
        raise typer.Exit(code=1)
    success(f"Backup created at {backup_workspace(destination)}")


@app.command()
@config_exists()
def restore(
    source: Path,
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help=(
            "Overwrite challenge files already on disk, and answer the "
            "--replace confirmation"
        ),
    ),
    replace: bool = typer.Option(
        False,
        "--replace",
        help="Discard the current metadata instead of merging into it",
    ),
) -> None:
    """Restore a full backup archive: challenge files, notes, and credentials."""
    from pwnv.utils import error, info, restore_workspace, success

    _confirm_replace(replace, force)

    try:
        summary = restore_workspace(source, replace=replace, force=force)
    except (FileNotFoundError, ValueError) as exc:
        error(str(exc))
        raise typer.Exit(code=1) from exc
    # A file that is not an archive at all, or one whose members refuse to
    # extract, raises a TarError. It is not a ValueError, so it used to reach
    # the user as a traceback.
    except tarfile.TarError as exc:
        error(f"{source} could not be read as a backup archive: {exc}")
        raise typer.Exit(code=1) from exc

    success(f"Workspace restored from {source}")
    info(f"Copied {summary['files_restored']} file(s) into the CTF folder.")
    _report_merge(summary, replace=replace)


@app.command(name="export")
@config_exists()
def export_(destination: Path = typer.Argument(Path("pwnv-export.json"))) -> None:
    """Export portable metadata without challenge files or credentials."""
    from pwnv.utils import export_workspace, success

    success(f"Workspace metadata exported to {export_workspace(destination)}")


@app.command(name="import")
@config_exists()
def import_(
    source: Path,
    force: bool = typer.Option(
        False, "--force", "-f", help="Answer the --replace confirmation"
    ),
    replace: bool = typer.Option(
        False,
        "--replace",
        help="Discard the current metadata instead of merging into it",
    ),
) -> None:
    """Merge a portable export into the current workspace."""
    from pwnv.utils import error, import_workspace, success

    _confirm_replace(replace, force)

    try:
        summary = import_workspace(source, replace=replace)
    except FileNotFoundError as exc:
        error(f"No export at {source}.")
        raise typer.Exit(code=1) from exc
    # Malformed JSON, or JSON that is not a workspace: both arrive as a
    # ValueError, and neither is worth a traceback.
    except ValueError as exc:
        error(f"{source} is not a pwnv export: {exc}")
        raise typer.Exit(code=1) from exc

    success(f"Workspace metadata imported from {source}")
    _report_merge(summary, replace=replace)
