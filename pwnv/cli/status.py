"""Workspace dashboard."""

import typer

from pwnv.utils import config_exists

app = typer.Typer(no_args_is_help=True)


@app.command()
@config_exists()
def status(
    ctf: str | None = typer.Option(None, "--ctf", help="Show one CTF only"),
    json_output: bool = typer.Option(
        False, "--json", help="Output machine-readable JSON"
    ),
) -> None:
    """Show challenge and point progress for the workspace."""
    import json
    from typing import cast

    from rich.console import Console
    from rich.table import Table

    from pwnv.models.challenge import Solved
    from pwnv.utils import challenges_for_ctf, error, get_ctf_by_name, get_ctfs

    ctfs = get_ctfs()
    if ctf:
        selected = get_ctf_by_name(ctf)
        if selected is None:
            error(f"CTF '{ctf}' does not exist.")
            raise typer.Exit(code=1)
        ctfs = [selected]

    rows = []
    for item in ctfs:
        challenges = challenges_for_ctf(item)
        solved = [ch for ch in challenges if ch.solved == Solved.solved]
        rows.append(
            {
                "ctf": item.name,
                "status": item.running.name,
                "solved": len(solved),
                "challenges": len(challenges),
                "earned_points": sum(ch.points or 0 for ch in solved),
                "total_points": sum(ch.points or 0 for ch in challenges),
                "categories": sorted({ch.category.name for ch in challenges}),
            }
        )

    if json_output:
        typer.echo(json.dumps(rows, indent=2))
        return

    table = Table(title="pwnv workspace")
    table.add_column("CTF")
    table.add_column("Status")
    table.add_column("Solved", justify="right")
    table.add_column("Points", justify="right")
    table.add_column("Categories")

    for row in rows:
        table.add_row(
            str(row["ctf"]),
            str(row["status"]),
            f"{row['solved']}/{row['challenges']}",
            f"{row['earned_points']}/{row['total_points']}",
            ", ".join(cast(list[str], row["categories"])) or "-",
        )

    Console().print(table)
