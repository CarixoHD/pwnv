import os
import shutil
import subprocess
from pathlib import Path
from typing import Annotated, Optional

import typer

from pwnv.cli.utils import error, get_config_path, save_config, success, warn
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
        error("`uv` binary not found in PATH. Install it first.")

        return

    cfg_path = get_config_path()
    if cfg_path.exists():
        error("Config file already exists - aborting.")

        return

    ctfs_folder = ctfs_folder.resolve()
    env_path = ctfs_folder / ".pwnvenv"

    if ctfs_folder.exists() and ctfs_folder.iterdir():
        typer.confirm(f"Directory {ctfs_folder} is not empty. Continue?", abort=True)
    else:
        typer.confirm(
            f"Create new CTF directory at {ctfs_folder}?", abort=True, default=True
        )

    # with Progress(
    #     SpinnerColumn(),
    #     TextColumn("[progress.description]{task.description}"),
    #     transient=True,
    # ) as bar:
    #     bar.add_task(description="Initialising workspace", start=False)

    ctfs_folder.mkdir(parents=True, exist_ok=True)
    init_model = Init(ctfs_path=ctfs_folder, challenge_tags=[], ctfs=[], challenges=[])
    save_config(init_model.model_dump())

    if (
        not subprocess.run(
            ["uv", "init", str(ctfs_folder), "--bare", "--vcs", "git"]
        ).returncode
        == 0
    ):
        error("Failed to initialise uv environment.")

        return
    os.chdir(ctfs_folder)
    if not subprocess.run(["uv", "add", *_PKGS]).returncode == 0:
        warn("Failed to add default packages.")

        return
    success(f"Activate with `source {env_path}/bin/activate`. Happy hacking!")
