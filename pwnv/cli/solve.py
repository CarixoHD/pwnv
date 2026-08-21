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
) -> None:
    """
    Marks a challenge as solved,
    optionally submitting the flag to a remote CTF and adding tags.
    """
    import asyncio

    from pwnv.models.challenge import Solved
    from pwnv.utils import (
        add_tags,
        get_challenge_by_name,
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

    unsolved = get_unsolved_challenges()
    if not unsolved:
        warn("No unsolved challenges found.")

        return

    named_challenge = get_challenge_by_name(challenge_name) if challenge_name else None
    if challenge_name and named_challenge is None:
        warn(f"Challenge '{challenge_name}' does not exist.")
        raise typer.Exit(code=1)
    if named_challenge and named_challenge not in unsolved:
        warn(f"Challenge '{challenge_name}' is already solved or does not exist.")
        raise typer.Exit(code=1)

    challenge = (
        named_challenge
        or (get_current_challenge() if get_current_challenge() in unsolved else None)
        or prompt_challenge_selection(unsolved, "Select a challenge:")
    )

    challenge.solved = Solved.solved
    if not flag:
        flag = prompt_text("Enter the flag:")

    if flag:
        challenge.flag = flag

    ctf = get_ctf_by_challenge(challenge)
    if ctf and ctf.url:
        if not asyncio.run(remote_solve(challenge=challenge, ctf=ctf, flag=flag)):
            warn("Remote submission failed or was rejected; keeping local solve state.")
    raw = tags if tags is not None else prompt_text("Enter tags (comma-separated):")
    if raw:
        parsed_tags = {t.strip().lower() for t in raw.split(",") if t.strip()}
        add_tags(parsed_tags)
        challenge.tags = sorted(parsed_tags)

    update_challenge(challenge)
    success(f"[cyan]{challenge.name}[/] marked as solved.")
