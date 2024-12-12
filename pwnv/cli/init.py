import typer
from rich import print
from typing import Annotated
from rich.progress import SpinnerColumn, Progress, TextColumn
from pathlib import Path
import shutil
import subprocess
import os
from pwnv.models import Init

app = typer.Typer(no_args_is_help=True)

testing = True


@app.command()
def init(
    env_path: Annotated[Path, "Path to the environment directory"] = Path.cwd()
    / "pwnvenv",
):
    app_config_path = Path(typer.get_app_dir("pwnv")) / "config.json"
    # env_path = Path(env_path).resolve() if env_path != "." else Path.cwd() / "pwnvenv"
    env_path = Path(env_path).resolve()

    if env_path.exists():
        typer.confirm(
            f"Directory {env_path} already exists. Continue?", abort=True, default=False
        )

    typer.confirm(
        f"Are you sure you want to initialize the environment in {env_path}?",
        abort=True,
        default=True,
    )

    if app_config_path.exists():
        print("[bold red]:x: Error:[/] Config file already exists.")
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Initializing environment", start=False)
        _create_app_config(app_config_path)

        init_model = Init(env_path=env_path, ctfs=[], challenges=[])
        if not _setup_virtualenv(env_path):
            return

        _write_config(init_model, app_config_path)

        print(
            f":tada: [green]Success![/] Run [green]`source {env_path}/bin/activate`[/] to activate the environment!"
        )


def _create_app_config(config_path: Path):
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.touch()


def _setup_virtualenv(env_path: Path) -> bool:
    uv = shutil.which("uv")
    if uv is None:
        print("[red]:x: Error:[/] uv binary not found in PATH. Please install it.")
        return False

    env_path.mkdir(parents=True, exist_ok=True)
    ret = subprocess.run(["uv", "venv", str(env_path)], capture_output=True)
    if ret.returncode != 0:
        print("[red]:x: Error:[/] Failed to create virtual environment.")
        return False

    packages = [
        "pwntools",
        "ropgadget",
        "angr",
        "spwn",
        "pycryptodome",
        "z3",
        "requests",
    ]
    os.chdir(env_path)
    ret = subprocess.run(["uv", "pip", "install", *packages], capture_output=True)
    if ret.returncode != 0:
        print("[red]:x: Error:[/] Failed to install packages.")
        return False

    return True


def _write_config(init_model: Init, config_path: Path):
    with open(config_path, "w") as config_file:
        config_file.write(init_model.model_dump_json())
