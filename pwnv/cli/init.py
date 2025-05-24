import os
import shutil
import subprocess
from pathlib import Path
from typing import Annotated, Optional

import typer

from pwnv.cli.utils import (
    command,
    error,
    get_config_path,
    info,
    prompt_confirm,
    save_config,
    warn,
)
from pwnv.models import Init

app = typer.Typer(no_args_is_help=True)

_PKGS = [
    "pwntools",
    "ropgadget",
    "angr",
    "spwn",
    "pycryptodome",
    "z3",
    "requests",
    "libdebug",
]


@app.command()
def init(
    ctfs_folder: Annotated[
        Optional[Path], typer.Option(help="Directory that will store all CTFs")
    ] = Path.cwd() / "CTF",
) -> None:
    if not shutil.which("uv"):
        error(f"{command('uv')} binary not found in PATH. Install it first.")
        return

    cfg_path = get_config_path()
    if cfg_path.exists():
        error("Config file already exists - aborting.")
        return

    ctfs_folder = ctfs_folder.resolve()
    env_path = ctfs_folder / ".pwnvenv"

    if ctfs_folder.exists() and ctfs_folder.iterdir():
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
    init_model = Init(ctfs_path=ctfs_folder, challenge_tags=[], ctfs=[], challenges=[])
    save_config(init_model.model_dump())

    if (
        not subprocess.run(
            ["uv", "venv", str(env_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    ):
        error("Failed to initialise uv environment.")

        return
    os.chdir(ctfs_folder)
    if not subprocess.run(["uv", "pip", "install", *_PKGS]).returncode == 0:
        warn("Failed to add default packages.")

        return
    info(f"Activate with {command(f'source {env_path}/bin/activate')}. Happy hacking!")
