"""Markdown challenge notes."""

from datetime import datetime

import typer

from pwnv.utils import challenges_exists, config_exists

app = typer.Typer(no_args_is_help=True, help="Manage challenge notes.")


@app.command()
@config_exists()
@challenges_exists()
def add(
    text: str,
    section: str = typer.Option("Findings", "--section", "-s"),
    challenge_name: str | None = typer.Option(None, "--challenge"),
    ctf: str | None = typer.Option(None, "--ctf"),
) -> None:
    """Append a timestamped entry to a challenge's NOTES.md file."""
    from pwnv.utils import resolve_challenge, success

    challenge = resolve_challenge(challenge_name=challenge_name, ctf_name=ctf)
    notes_path = challenge.path / "NOTES.md"
    if not notes_path.exists():
        notes_path.write_text(f"# {challenge.name}\n", encoding="utf-8")
    timestamp = datetime.now().astimezone().isoformat(timespec="minutes")
    with notes_path.open("a", encoding="utf-8") as notes:
        notes.write(f"\n## {section}\n\n- [{timestamp}] {text}\n")
    success(f"Note added to {notes_path}")


@app.command()
@config_exists()
@challenges_exists()
def show(
    challenge_name: str | None = typer.Option(None, "--challenge"),
    ctf: str | None = typer.Option(None, "--ctf"),
) -> None:
    """Render a challenge's NOTES.md file."""
    from rich.console import Console
    from rich.markdown import Markdown

    from pwnv.utils import resolve_challenge, warn

    challenge = resolve_challenge(challenge_name=challenge_name, ctf_name=ctf)
    notes_path = challenge.path / "NOTES.md"
    if not notes_path.exists():
        warn(f"No notes found for {challenge.name}.")
        return
    Console().print(Markdown(notes_path.read_text(encoding="utf-8")))
