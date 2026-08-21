"""Workspace health checks."""

import typer

from pwnv.utils import config_exists

app = typer.Typer(no_args_is_help=True)


@app.command()
@config_exists()
def doctor() -> None:
    """Check configuration, paths, tools, and workspace consistency."""
    import shutil

    from pydantic import ValidationError
    from rich import print

    from pwnv.models import Init
    from pwnv.utils import get_config_path, load_config

    checks: list[tuple[bool, str]] = []
    config_path = get_config_path()
    checks.append((config_path.is_file(), f"Configuration: {config_path}"))

    try:
        config = Init.model_validate(load_config())
    except (ValidationError, ValueError, TypeError) as exc:
        print(f"[red]✗[/] Invalid configuration: {exc}")
        raise typer.Exit(code=1)

    checks.append((config.ctfs_path.is_dir(), f"CTF root: {config.ctfs_path}"))
    checks.append((shutil.which("uv") is not None, "uv available in PATH"))

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

    print(f"\n{len(checks) - failures} passed, {failures} failed")
    if failures:
        raise typer.Exit(code=1)
