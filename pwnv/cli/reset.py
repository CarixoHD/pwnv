import shutil
import tempfile
from pathlib import Path

import typer

from pwnv.constants import DEFAULT_PWNVENV_FOLDER_NAME
from pwnv.utils import (
    command,
    config_exists,
    get_config_path,
    get_ctfs_path,
    info,
    prompt_confirm,
    success,
    warn,
)

app = typer.Typer(no_args_is_help=True)


@app.command()
@config_exists()
def reset(
    force: bool = typer.Option(
        False, "--force", "-f", help="Force reset without confirmation"
    ),
) -> None:
    """
    Resets the pwnv environment by removing all CTFs and configuration files,
    with an option to create a backup.
    """
    from rich import print

    ctfs_path = get_ctfs_path()
    cfg_path = get_config_path()

    if not force:
        print("[red]" + "-" * 40 + " WARNING! " + "-" * 40 + "[/]")
        if not prompt_confirm(
            f"This will delete all CTFs and config at:\n{ctfs_path}\n{cfg_path.parent}"
            "\nContinue?",
            default=False,
        ):
            warn("Aborting reset.")
            return

    if not force and prompt_confirm(
        "Do you want to backup the current environment as a tar.gz file?",
        default=False,
    ):
        backup_base = Path.home() / "pwnv_backup"
        backup_archive = backup_base.with_suffix(".tar.gz")

        if backup_archive.exists():
            if not prompt_confirm(
                f"Backup file already exists at {backup_archive}. Overwrite?",
                default=False,
            ):
                warn("Aborting backup creation.")
                return
            backup_archive.unlink()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)

                def ignore_pwnvenv(dir, contents):
                    return (
                        [DEFAULT_PWNVENV_FOLDER_NAME]
                        if DEFAULT_PWNVENV_FOLDER_NAME in contents
                        else []
                    )

                shutil.copytree(ctfs_path, tmp / ctfs_path.name, ignore=ignore_pwnvenv)
                shutil.copy(cfg_path, tmp / cfg_path.name)

                shutil.make_archive(str(backup_base), "gztar", root_dir=tmp)

            success(f"Backup created at {backup_archive}")
        except Exception as e:
            warn(f"Backup failed: {e}")

    if ctfs_path.exists():
        shutil.rmtree(ctfs_path)
        success(f"Removed CTF files at {ctfs_path}")
    else:
        info("No CTF files found - nothing to remove.")

    if cfg_path.parent.exists():
        shutil.rmtree(cfg_path.parent)
        success(f"Removed {cfg_path.parent} config directory")
    else:
        info("No config path found - nothing to remove.")

    success("Workspace reset complete!")
    info(f"Run {command('pwnv init')} to bootstrap a fresh environment.")
