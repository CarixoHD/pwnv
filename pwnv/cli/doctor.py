import typer

from pwnv.utils import config_exists

app = typer.Typer(no_args_is_help=True)


@app.command()
@config_exists()
def doctor() -> None:
    """Checks configuration, paths, tools, and workspace consistency."""
    import shutil

    from pydantic import ValidationError
    from rich import print

    from pwnv.constants import DEFAULT_PACKAGES, DEFAULT_PYTHON_VERSION
    from pwnv.models import Init
    from pwnv.utils import (
        ctf_env_path,
        get_config_path,
        installed_packages,
        load_config,
        venv_python,
    )

    checks: list[tuple[bool, str]] = []
    warnings: list[str] = []
    config_path = get_config_path()
    checks.append((config_path.is_file(), f"Configuration: {config_path}"))

    try:
        config = Init.model_validate(load_config())
    except (ValidationError, ValueError, TypeError) as exc:
        print(f"[red]✗[/] Invalid configuration: {exc}")
        raise typer.Exit(code=1)

    checks.append((config.ctfs_path.is_dir(), f"CTF root: {config.ctfs_path}"))
    checks.append((shutil.which("uv") is not None, "uv available in PATH"))

    environment = ctf_env_path(config.ctfs_path)
    interpreter = venv_python(environment)
    if not interpreter.is_file():
        warnings.append(
            f"No CTF environment at {environment} - recreate it with "
            f"`uv venv --python {DEFAULT_PYTHON_VERSION} {environment}` "
            "or a fresh `pwnv init`"
        )
    else:
        checks.append((True, f"CTF environment: {environment}"))
        packages = installed_packages(interpreter)
        if packages is None:
            warnings.append(f"Could not inspect the packages in {environment}")
        else:
            missing = [
                name
                for name in DEFAULT_PACKAGES
                if name.lower().replace("_", "-") not in packages
            ]
            if missing:
                warnings.append(
                    f"Missing default packages: {', '.join(missing)} - install them "
                    f"with `uv pip install --python {interpreter} {' '.join(missing)}`"
                )
            else:
                checks.append((True, "Default packages installed"))

    ctf_ids = [ctf.id for ctf in config.ctfs if ctf is not None]
    challenge_ids = [ch.id for ch in config.challenges if ch is not None]
    checks.append((len(ctf_ids) == len(set(ctf_ids)), "Unique CTF IDs"))
    checks.append(
        (len(challenge_ids) == len(set(challenge_ids)), "Unique challenge IDs")
    )

    valid_ctf_ids = set(ctf_ids)
    for ctf in config.ctfs:
        if ctf is not None:
            checks.append((ctf.path.is_dir(), f"CTF directory: {ctf.name}"))
            if ctf.url:
                checks.append(
                    (
                        (ctf.path / ".session").is_file()
                        or (ctf.path / ".env").is_file(),
                        f"Remote credentials/session: {ctf.name}",
                    )
                )
    for challenge in config.challenges:
        if challenge is not None:
            checks.append(
                (
                    challenge.ctf_id in valid_ctf_ids,
                    f"Challenge parent: {challenge.name}",
                )
            )
            checks.append(
                (challenge.path.is_dir(), f"Challenge directory: {challenge.name}")
            )

    failures = 0
    for passed, message in checks:
        print(f"[{'green' if passed else 'red'}]{'✓' if passed else '✗'}[/] {message}")
        failures += not passed

    for message in warnings:
        print(f"[yellow]![/] {message}")

    summary = f"\n{len(checks) - failures} passed, {failures} failed"
    if warnings:
        summary += f", {len(warnings)} warning{'s' if len(warnings) > 1 else ''}"
    print(summary)
    if failures:
        raise typer.Exit(code=1)
