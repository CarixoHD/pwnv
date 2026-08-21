"""Per-challenge Python environments."""

from pathlib import Path

import typer

from pwnv.utils import challenges_exists, config_exists

app = typer.Typer(no_args_is_help=True, help="Manage a challenge's uv environment.")


def _python_path(environment: Path) -> Path:
    windows = environment / "Scripts" / "python.exe"
    return windows if windows.exists() else environment / "bin" / "python"


def _ensure_environment(challenge_path: Path) -> Path:
    import shutil
    import subprocess

    from pwnv.utils import command, error

    if not shutil.which("uv"):
        error(f"{command('uv')} binary not found in PATH.")
        raise typer.Exit(code=1)
    environment = challenge_path / ".venv"
    if not _python_path(environment).exists():
        result = subprocess.run(["uv", "venv", str(environment)], check=False)
        if result.returncode:
            error("Failed to create the challenge environment.")
            raise typer.Exit(code=result.returncode)
    return environment


@app.command()
@config_exists()
@challenges_exists()
def add(
    packages: list[str] = typer.Argument(..., help="Packages to install"),
    challenge_name: str | None = typer.Option(None, "--challenge"),
    ctf: str | None = typer.Option(None, "--ctf"),
) -> None:
    """Install packages into a challenge-local virtual environment."""
    import subprocess

    from pwnv.utils import error, resolve_challenge, success

    challenge = resolve_challenge(challenge_name=challenge_name, ctf_name=ctf)
    environment = _ensure_environment(challenge.path)
    result = subprocess.run(
        ["uv", "pip", "install", "--python", str(_python_path(environment)), *packages],
        cwd=challenge.path,
        check=False,
    )
    if result.returncode:
        error("Failed to install one or more packages.")
        raise typer.Exit(code=result.returncode)
    success(f"Installed {', '.join(packages)} in {environment}")


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
@config_exists()
@challenges_exists()
def run(
    ctx: typer.Context,
    challenge_name: str | None = typer.Option(None, "--challenge"),
    ctf: str | None = typer.Option(None, "--ctf"),
) -> None:
    """Run a command with the challenge environment on PATH."""
    import os
    import subprocess

    from pwnv.utils import error, resolve_challenge

    if not ctx.args:
        error("Provide a command to run after the options.")
        raise typer.Exit(code=1)
    challenge = resolve_challenge(challenge_name=challenge_name, ctf_name=ctf)
    environment = _ensure_environment(challenge.path)
    bin_path = _python_path(environment).parent
    process_env = os.environ.copy()
    process_env["VIRTUAL_ENV"] = str(environment)
    process_env["PATH"] = os.pathsep.join([str(bin_path), process_env.get("PATH", "")])
    result = subprocess.run(ctx.args, cwd=challenge.path, env=process_env, check=False)
    if result.returncode:
        raise typer.Exit(code=result.returncode)
