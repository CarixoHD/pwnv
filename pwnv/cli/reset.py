import shutil
from pathlib import Path

import typer
from rich import print

from pwnv.cli.utils import (
    config_exists,
    confirm,
    get_config_path,
    get_ctfs_path,
    success,
)

app = typer.Typer(no_args_is_help=True)


@app.command()
@config_exists()
def reset() -> None:
    if not confirm(
        "This will delete the entire environment (config + files). Continue?",
        default=False,
    ):
        print("[red]:x:[/] Aborted.")
        return

    env_path: Path = get_ctfs_path()
    if env_path.exists() and confirm(
        "Delete all CTF and challenge directories as well?", default=False
    ):
        shutil.rmtree(env_path)
        success(f"Deleted workspace files at {env_path}")

    else:
        success("Skipped workspace directory deletion.")

    cfg_path = get_config_path()
    if cfg_path.exists():
        cfg_path.unlink()
        success(f"Removed config file at {cfg_path}")

    else:
        success("No config file found - nothing to remove.")

    success("Workspace reset complete!")

    print("Run [magenta]`pwnv init`[/] to bootstrap a fresh environment.")
