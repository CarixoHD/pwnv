from pathlib import Path

from pwnv.constants import DEFAULT_PWNVENV_FOLDER_NAME


def venv_python(environment: Path) -> Path:
    windows = environment / "Scripts" / "python.exe"
    return windows if windows.exists() else environment / "bin" / "python"


def ctf_env_path(ctfs_path: Path | None = None) -> Path:
    if ctfs_path is None:
        from pwnv.utils.config import get_ctfs_path

        ctfs_path = get_ctfs_path()
    return ctfs_path / DEFAULT_PWNVENV_FOLDER_NAME


def installed_packages(python_path: Path) -> set[str] | None:
    import json
    import shutil
    import subprocess

    if not shutil.which("uv") or not python_path.exists():
        return None
    result = subprocess.run(
        ["uv", "pip", "list", "--python", str(python_path), "--format", "json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        return None
    try:
        packages = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    return {str(package["name"]).lower().replace("_", "-") for package in packages}
