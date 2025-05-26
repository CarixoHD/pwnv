import os
import shutil
import subprocess
from pathlib import Path
from typing import Annotated, Optional

import typer

from pwnv.constants import (
    DEFAULT_CTFS_FOLDER_NAME,
    DEFAULT_PACKAGES,
    DEFAULT_PLUGINS_FOLDER_NAME,
    DEFAULT_PWNVENV_FOLDER_NAME,
    DEFAULT_TEMPLATES_FOLDER_NAME,
)
from pwnv.models import Init
from pwnv.utils import (
    command,
    error,
    get_config_path,
    info,
    prompt_confirm,
    save_config,
    warn,
)

app = typer.Typer(no_args_is_help=True)


@app.command()
def init(
    ctfs_folder: Annotated[
        Optional[Path], typer.Option(help="Directory that will store all CTFs")
    ] = Path.cwd() / DEFAULT_CTFS_FOLDER_NAME,
    no_install: Annotated[
        bool, typer.Option(help="Skip installation of default packages")
    ] = False,
) -> None:
    """
    Initializes a new pwnv environment, setting up the necessary directories and
    virtual environment.
    """
    if not shutil.which("uv"):
        error(f"{command('uv')} binary not found in PATH. Install it first.")
        return

    cfg_path = get_config_path()
    plugin_folder = cfg_path.parent / DEFAULT_PLUGINS_FOLDER_NAME
    templates_folder = cfg_path.parent / DEFAULT_TEMPLATES_FOLDER_NAME

    if cfg_path.exists():
        error("Config file already exists - aborting.")
        return

    ctfs_folder = ctfs_folder.resolve()
    env_path = ctfs_folder / DEFAULT_PWNVENV_FOLDER_NAME

    if ctfs_folder.exists() and any(ctfs_folder.iterdir()):
        if not prompt_confirm(
            f"Directory {ctfs_folder} already exists. Continue?", default=False
        ):
            return
    else:
        if not prompt_confirm(
            f"Create new CTF directory at {ctfs_folder}?", default=True
        ):
            return

    ctfs_folder.mkdir(parents=True, exist_ok=True)
    plugin_folder.mkdir(parents=True, exist_ok=True)
    templates_folder.mkdir(parents=True, exist_ok=True)

    init_model = Init(ctfs_path=ctfs_folder, challenge_tags=[], ctfs=[], challenges=[])
    save_config(init_model.model_dump())

    if not (
        subprocess.run(
            ["uv", "venv", str(env_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    ):
        error("Failed to initialise uv environment.")
        info(f"Run {command('pwnv reset')} and run {command('pwnv init')} again.")
        return

    if not no_install:
        os.chdir(ctfs_folder)
        if (
            not subprocess.run(["uv", "pip", "install", *DEFAULT_PACKAGES]).returncode
            == 0
        ):
            warn("Failed to add default packages.")
            info(f"Run {command('pwnv reset')} and run {command('pwnv init')} again.")
            return

    info(f"Activate with {command(f'source {env_path}/bin/activate')}. Happy hacking!")
