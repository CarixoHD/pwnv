import asyncio

import typer

from pwnv.cli.utils import (
    add_tags,
    challenges_exists,
    config_exists,
    get_ctf_by_challenge,
    get_current_challenge,
    get_unsolved_challenges,
    prompt_challenge_selection,
    prompt_text,
    remote_solve,
    success,
    update_challenge,
    warn,
)
from pwnv.models.challenge import Solved

app = typer.Typer(no_args_is_help=True)


@app.command()
@config_exists()
@challenges_exists()
def solve(flag: str = "") -> None:
    unsolved = get_unsolved_challenges()
    if not unsolved:
        warn("No unsolved challenges found.")

        return

    challenge = (
        get_current_challenge() if get_current_challenge() in unsolved else None
    ) or prompt_challenge_selection(unsolved, "Select a challenge:")

    challenge.solved = Solved.solved
    if not flag:
        flag = prompt_text("Enter the flag:")

    if flag:
        challenge.flag = flag

    ctf = get_ctf_by_challenge(challenge)
    if (ctf.path / ".env").exists():
        if not asyncio.run(remote_solve(challenge=challenge, ctf=ctf, flag=flag)):
            return
    raw = prompt_text("Enter tags (comma-separated):")
    if raw:
        tags = {t.strip().lower() for t in raw.split(",") if t.strip()}
        add_tags(tags)
        challenge.tags = sorted(tags)

    update_challenge(challenge)
    success(f"[cyan]{challenge.name}[/] marked as solved.")
