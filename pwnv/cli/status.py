import typer

from pwnv.cli.options import JSON
from pwnv.utils import config_exists

app = typer.Typer(no_args_is_help=True)


def _last_solve(challenge) -> str | None:
    extras = challenge.extras if isinstance(challenge.extras, dict) else {}
    attempts = [
        attempt
        for attempt in extras.get("flag_history", [])
        if isinstance(attempt, dict) and attempt.get("result") in ("accepted", "local")
    ]
    return str(attempts[-1].get("timestamp")) if attempts else None


def _ctf_row(ctf, challenges) -> dict:
    from pwnv.models.challenge import Solved

    solved = [ch for ch in challenges if ch.solved == Solved.solved]
    return {
        "ctf": ctf.name,
        "status": ctf.running.name,
        "remote": bool(ctf.url),
        "solved": len(solved),
        "challenges": len(challenges),
        "earned_points": sum(ch.points or 0 for ch in solved),
        "total_points": sum(ch.points or 0 for ch in challenges),
        "categories": sorted({ch.category.name for ch in challenges}),
    }


def _category_rows(challenges) -> list[dict]:
    from pwnv.models.challenge import Solved

    rows: dict[str, dict] = {}
    for challenge in challenges:
        row = rows.setdefault(
            challenge.category.name,
            {"category": challenge.category.name, "solved": 0, "total": 0, "points": 0},
        )
        row["total"] += 1
        if challenge.solved == Solved.solved:
            row["solved"] += 1
            row["points"] += challenge.points or 0
    return sorted(rows.values(), key=lambda row: row["category"])


def _todo(challenges, limit: int) -> list[dict]:
    from pwnv.models.challenge import Solved
    from pwnv.utils import format_service

    unsolved = [ch for ch in challenges if ch.solved != Solved.solved]
    unsolved.sort(key=lambda ch: (ch.points or 0, ch.name))
    rows = []
    for challenge in unsolved[:limit]:
        extras = challenge.extras if isinstance(challenge.extras, dict) else {}
        services = extras.get("services") or []
        rows.append(
            {
                "name": challenge.name,
                "category": challenge.category.name,
                "points": challenge.points,
                "service": format_service(services[0]) if services else "",
                "attachments": len(extras.get("attachments") or []),
            }
        )
    return rows


def _recent_solves(challenges, limit: int) -> list[dict]:
    from pwnv.models.challenge import Solved

    solved = [
        {
            "name": ch.name,
            "category": ch.category.name,
            "points": ch.points,
            "solved_at": _last_solve(ch),
        }
        for ch in challenges
        if ch.solved == Solved.solved
    ]
    solved.sort(key=lambda row: row["solved_at"] or "", reverse=True)
    return solved[:limit]


@app.command()
@config_exists()
def status(
    ctf: str | None = typer.Option(None, "--ctf", help="Show one CTF only"),
    detail: bool = typer.Option(
        False,
        "--detail",
        "-d",
        help="Add per-category progress, recent solves, and what is left",
    ),
    limit: int = typer.Option(
        5, "--limit", min=1, help="Rows to show in the detail tables"
    ),
    json_output: bool = JSON,
) -> None:
    """Shows challenge and point progress for the workspace."""
    from typing import Any, cast

    from rich.console import Console
    from rich.table import Table

    from pwnv.utils import (
        emit_json,
        error,
        get_challenges,
        get_ctf_by_name,
        get_ctfs,
        get_current_challenge,
        get_current_ctf,
        info,
    )

    ctfs = get_ctfs()
    if ctf:
        selected = get_ctf_by_name(ctf)
        if selected is None:
            error(f"CTF '{ctf}' does not exist.")
            raise typer.Exit(code=1)
        ctfs = [selected]

    grouped: dict[Any, list] = {}
    for item in get_challenges():
        grouped.setdefault(item.ctf_id, []).append(item)

    rows = [_ctf_row(item, grouped.get(item.id, [])) for item in ctfs]

    focus = ctfs[0] if len(ctfs) == 1 else get_current_ctf()
    focus_challenges = grouped.get(focus.id, []) if focus else []
    detail_payload: dict[str, Any] | None = (
        {
            "ctf": focus.name,
            "categories": _category_rows(focus_challenges),
            "recent_solves": _recent_solves(focus_challenges, limit),
            "next_up": _todo(focus_challenges, limit),
        }
        if detail and focus
        else None
    )

    if json_output:
        payload: dict = {"ctfs": rows}
        current_challenge = get_current_challenge()
        payload["current"] = {
            "ctf": focus.name if focus else None,
            "challenge": current_challenge.name if current_challenge else None,
        }
        if detail_payload:
            payload["detail"] = detail_payload
        emit_json(payload)
        return

    console = Console()

    table = Table(title="pwnv workspace")
    table.add_column("CTF")
    table.add_column("Status")
    table.add_column("Kind")
    table.add_column("Solved", justify="right")
    table.add_column("Points", justify="right")
    table.add_column("Categories")

    for row in rows:
        table.add_row(
            str(row["ctf"]),
            str(row["status"]),
            "remote" if row["remote"] else "local",
            f"{row['solved']}/{row['challenges']}",
            f"{row['earned_points']}/{row['total_points']}",
            ", ".join(cast(list[str], row["categories"])) or "-",
        )

    console.print(table)

    current_challenge = get_current_challenge()
    if current_challenge:
        info(
            f"You are in [cyan]{current_challenge.name}[/] "
            f"({current_challenge.category.name})."
        )
    elif focus:
        info(f"You are in [cyan]{focus.name}[/].")

    if detail_payload is None or focus is None:
        if detail:
            info("Pick a CTF with --ctf, or run this from inside one, to see detail.")
        return

    categories = Table(title=f"{focus.name} by category")
    categories.add_column("Category")
    categories.add_column("Solved", justify="right")
    categories.add_column("Points", justify="right")
    for category_row in detail_payload["categories"]:
        categories.add_row(
            str(category_row["category"]),
            f"{category_row['solved']}/{category_row['total']}",
            str(category_row["points"]),
        )
    console.print(categories)

    if recent := detail_payload["recent_solves"]:
        solves = Table(title="Recent solves")
        solves.add_column("Challenge")
        solves.add_column("Category")
        solves.add_column("Points", justify="right")
        solves.add_column("When")
        for solve_row in recent:
            solves.add_row(
                str(solve_row["name"]),
                str(solve_row["category"]),
                str(solve_row["points"] if solve_row["points"] is not None else "-"),
                str(solve_row["solved_at"] or "-"),
            )
        console.print(solves)

    if next_up := detail_payload["next_up"]:
        todo = Table(title="Next up (cheapest first)")
        todo.add_column("Challenge")
        todo.add_column("Category")
        todo.add_column("Points", justify="right")
        todo.add_column("Service")
        todo.add_column("Files", justify="right")
        for todo_row in next_up:
            todo.add_row(
                str(todo_row["name"]),
                str(todo_row["category"]),
                str(todo_row["points"] if todo_row["points"] is not None else "-"),
                str(todo_row["service"] or "-"),
                str(todo_row["attachments"]),
            )
        console.print(todo)
