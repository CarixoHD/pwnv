from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import typer

from pwnv.constants import (
    DEFAULT_CTFS_FOLDER_NAME,
    DEFAULT_PACKAGES,
    DEFAULT_PLUGINS_FOLDER_NAME,
    DEFAULT_PWNVENV_FOLDER_NAME,
    DEFAULT_PYTHON_VERSION,
    DEFAULT_TEMPLATES_FOLDER_NAME,
)

if TYPE_CHECKING:
    from subprocess import CompletedProcess

app = typer.Typer(no_args_is_help=True)


def _report(result: CompletedProcess[str]) -> None:
    from pwnv.utils import warn

    output = (result.stderr or result.stdout or "").strip()
    if output:
        warn(output)


@app.command()
def init(
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Accept directory creation prompts for unattended setup",
    ),
    no_install: bool = typer.Option(
        False,
        "--no-install",
        "-n",
        help="Do not install default packages in the virtual environment",
    ),
    no_examples: bool = typer.Option(
        False,
        "--no-examples",
        help="Do not copy the bundled example plugins and templates",
    ),
    ctfs_folder: Path = typer.Option(
        Path.cwd() / DEFAULT_CTFS_FOLDER_NAME,
        "--ctfs-folder",
        "-f",
        help="Directory that will store all CTFs",
    ),
    python: str = typer.Option(
        DEFAULT_PYTHON_VERSION,
        "--python",
        "-p",
        help="Python version or interpreter for the CTF environment",
    ),
) -> None:
    """
    Initializes a new pwnv environment, setting up the necessary directories and
    virtual environment.
    """
    import shutil
    import subprocess

    from pwnv.models import Init
    from pwnv.utils import (
        command,
        error,
        get_config_path,
        info,
        install_bundled_examples,
        prompt_confirm,
        save_config,
        success,
        venv_python,
        warn,
    )

    if not shutil.which("uv"):
        error(f"{command('uv')} binary not found in PATH. Install it first.")
        raise typer.Exit(code=1)

    cfg_path = get_config_path()
    plugin_folder = cfg_path.parent / DEFAULT_PLUGINS_FOLDER_NAME
    templates_folder = cfg_path.parent / DEFAULT_TEMPLATES_FOLDER_NAME

    if cfg_path.exists():
        error("Config file already exists - aborting.")
        raise typer.Exit(code=1)

    ctfs_folder = ctfs_folder.resolve()
    env_path = ctfs_folder / DEFAULT_PWNVENV_FOLDER_NAME

    if not yes and ctfs_folder.exists() and any(ctfs_folder.iterdir()):
        if not prompt_confirm(
            f"Directory {ctfs_folder} already exists. Continue?", default=False
        ):
            return
    elif not yes:
        if not prompt_confirm(
            f"Create new CTF directory at {ctfs_folder}?", default=True
        ):
            return

    ctfs_folder.mkdir(parents=True, exist_ok=True)
    plugin_folder.mkdir(parents=True, exist_ok=True)
    templates_folder.mkdir(parents=True, exist_ok=True)

    init_model = Init(ctfs_path=ctfs_folder, challenge_tags=[], ctfs=[], challenges=[])
    save_config(init_model.model_dump())

    if not no_examples:
        installed = install_bundled_examples()
        if installed:
            success(
                f"Copied {len(installed)} example plugin file(s) into "
                f"{plugin_folder} and {templates_folder}."
            )

    venv = subprocess.run(
        ["uv", "venv", "--python", python, str(env_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if venv.returncode:
        error("Failed to initialise uv environment.")
        _report(venv)
        info(f"Run {command('pwnv reset')} and run {command('pwnv init')} again.")
        raise typer.Exit(code=1)

    python_path = venv_python(env_path)

    if not no_install:
        info(
            f"Installing {len(DEFAULT_PACKAGES)} default packages - "
            "this may take a while."
        )
        install = subprocess.run(
            ["uv", "pip", "install", "--python", str(python_path), *DEFAULT_PACKAGES],
            cwd=ctfs_folder,
            check=False,
        )
        if install.returncode:
            warn("Failed to add default packages.")
            info(f"Run {command('pwnv reset')} and run {command('pwnv init')} again.")
            return

        health_check = subprocess.run(
            ["uv", "pip", "check", "--python", str(python_path)],
            cwd=ctfs_folder,
            capture_output=True,
            text=True,
            check=False,
        )
        if health_check.returncode:
            warn("The CTF environment contains incompatible packages.")
            _report(health_check)
            info(f"Run {command('pwnv doctor')} for details.")
        else:
            success(f"Installed default packages into {env_path}.")

    info(f"Activate with {command(f'source {env_path}/bin/activate')}. Happy hacking!")
