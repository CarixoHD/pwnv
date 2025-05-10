import typer
from rich import print
from typing import Annotated, Optional
from rich.progress import SpinnerColumn, Progress, TextColumn
from pathlib import Path
import shutil
import subprocess
import os
from pwnv.models import Init
from pwnv.cli.utils import get_config


app = typer.Typer(no_args_is_help=True)


@app.command()
def init(
    ctfs_folder: Annotated[
        Optional[Path], typer.Option(help="Path to the new directory to store CTFs")
    ] = Path.cwd()
    / "CTF",
):
    uv = shutil.which("uv")
    if uv is None:
        print("[red]:x: Error:[/] uv binary not found in PATH. Please install it.")
        return
    config_path = get_config()
    if config_path.exists():
        print("[bold red]:x: Error:[/] Config file already exists.")
        return

    ctfs_folder = ctfs_folder.resolve()
    env_path = ctfs_folder / ".pwnvenv"
    if ctfs_folder.exists():
        typer.confirm(
            f"Directory {ctfs_folder} already exists. Continue?",
            abort=True,
            default=False,
        )

    typer.confirm(
        f"Create new CTF directory at {ctfs_folder}?",
        abort=True,
        default=True,
    )

    # if config_path.exists():
    #     print("[bold red]:x: Error:[/] Config file already exists.")
    #     return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Initializing environment", start=False)
        create_app_config(config_path)
        init_model = Init(
            ctfs_path=ctfs_folder,
            challenge_tags=[],
            ctfs=[],
            challenges=[],
        )
        if not setup_ctf_env(ctfs_folder):
            return

        write_config(init_model, config_path)

        print(
            f":tada: [green]Success![/] Run [green]`source {env_path}/bin/activate`[/] to activate the environment!"
        )


def create_app_config(config_path: Path):
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.touch()


def setup_ctf_env(ctf_path: Path) -> bool:
    command = ["uv", "init", str(ctf_path), "--bare", "--vcs", "git"]
    print(f"Running command: {' '.join(command)}")
    ret = subprocess.run(command, capture_output=True)
    print(ret.stdout.decode())
    if ret.returncode != 0:
        print("[red]:x: Error:[/] Failed to initialize CTF environment.")
        return False

    packages = [
        "pwntools",
        "ropgadget",
        "angr",
        "spwn",
        "pycryptodome",
        "z3",
        "requests",
        "libdebug",
    ]
    os.chdir(ctf_path)
    ret = subprocess.run(["uv", "add", *packages], capture_output=True)
    if ret.returncode != 0:
        print("[red]:x: Error:[/] Failed to add packages.")
        return False

    return True


def write_config(init_model: Init, config_path: Path):
    with open(config_path, "w") as config_file:
        config_file.write(init_model.model_dump_json())
