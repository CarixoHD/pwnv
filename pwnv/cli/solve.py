import typer

from pwnv.utils import (
    challenges_exists,
    config_exists,
)

app = typer.Typer(no_args_is_help=True)


@app.command()
@config_exists()
@challenges_exists()
def solve(
    flag: str = "",
    challenge_name: str | None = typer.Option(
        None, "--challenge", help="Challenge name (skips selection)"
    ),
    tags: str | None = typer.Option(
        None, "--tags", help="Comma-separated tags (skips prompt)"
    ),
    ctf: str | None = typer.Option(None, "--ctf", help="Limit selection to one CTF"),
    history: bool = typer.Option(False, "--history", help="Show submission history"),
    show_flags: bool = typer.Option(
        False, "--show-flags", help="Show stored flags in submission history"
    ),
) -> None:
    """
    Marks a challenge as solved,
    optionally submitting the flag to a remote CTF and adding tags.
    """
    import asyncio
    from datetime import datetime

    from pwnv.models.challenge import Solved
    from pwnv.utils import (
        add_tags,
        get_challenges,
        get_ctf_by_challenge,
        get_unsolved_challenges,
        prompt_text,
        remote_solve,
        resolve_challenge,
        success,
        update_challenge,
        warn,
    )

    if show_flags and not history:
        warn("--show-flags only applies with --history.")
        raise typer.Exit(code=1)

    if history:
        from rich.console import Console
        from rich.table import Table

        challenge = resolve_challenge(
            challenge_name=challenge_name,
            ctf_name=ctf,
            challenges=get_challenges(),
            prompt="Select a challenge to show history:",
        )
        attempts = (
            challenge.extras.get("flag_history", [])
            if isinstance(challenge.extras, dict)
            else []
        )
        if not attempts:
            warn(f"No submission history found for {challenge.name}.")
            return
        table = Table(title=f"Submission history: {challenge.name}")
        table.add_column("Time")
        table.add_column("Result")
        table.add_column("Flag")
        for attempt in attempts:
            stored_flag = str(attempt.get("flag", ""))
            displayed_flag = stored_flag if show_flags else "••••••••"
            table.add_row(
                str(attempt.get("timestamp", "")),
                str(attempt.get("result", "unknown")),
                displayed_flag,
            )
        Console().print(table)
        return

    unsolved = get_unsolved_challenges()
    if not unsolved:
        warn("No unsolved challenges found.")

        return

    challenge = resolve_challenge(
        challenge_name=challenge_name,
        ctf_name=ctf,
        challenges=unsolved,
        prompt="Select a challenge:",
    )

    if not flag:
        flag = prompt_text("Enter the flag:")

    parent_ctf = get_ctf_by_challenge(challenge)
    result = "local"
    accepted = True
    if parent_ctf and parent_ctf.url:
        accepted = asyncio.run(
            remote_solve(challenge=challenge, ctf=parent_ctf, flag=flag)
        )
        result = "accepted" if accepted else "rejected-or-failed"

    if accepted:
        challenge.solved = Solved.solved
        if flag:
            challenge.flag = flag

    extras = dict(challenge.extras or {})
    attempts = list(extras.get("flag_history", []))
    attempts.append(
        {
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "result": result,
            "flag": flag,
        }
    )
    extras["flag_history"] = attempts
    challenge.extras = extras

    if not accepted:
        update_challenge(challenge)
        warn(
            f"[cyan]{challenge.name}[/] was NOT marked as solved - "
            "the platform rejected the flag or the submission failed."
        )
        raise typer.Exit(code=1)

    raw = tags if tags is not None else prompt_text("Enter tags (comma-separated):")
    if raw:
        parsed_tags = {t.strip().lower() for t in raw.split(",") if t.strip()}
        add_tags(parsed_tags)
        challenge.tags = sorted(parsed_tags)

    update_challenge(challenge)
    success(f"[cyan]{challenge.name}[/] marked as solved.")
