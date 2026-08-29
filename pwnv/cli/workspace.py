from pathlib import Path

import typer

from pwnv.utils import config_exists

app = typer.Typer(no_args_is_help=True, help="Back up and transfer workspaces.")


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
    force: bool = typer.Option(False, "--force", "-f"),
) -> None:
    """Replace current metadata with a portable export."""
    from pwnv.utils import (
        get_challenges,
        get_ctfs,
        import_workspace,
        prompt_confirm,
        success,
    )

    if (get_ctfs() or get_challenges()) and not force:
        if not prompt_confirm("Replace the current workspace metadata?", default=False):
            raise typer.Abort()
    import_workspace(source)
    success(f"Workspace metadata imported from {source}")
