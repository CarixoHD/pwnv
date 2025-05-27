import typer

from pwnv.cli import (
    challenge_app,
    ctf_app,
    init_app,
    plugin_app,
    reset_app,
    solve_app,
)


def main():
    app = typer.Typer(no_args_is_help=True)
    app.add_typer(challenge_app, name="challenge")
    app.add_typer(ctf_app, name="ctf")
    app.add_typer(init_app)
    app.add_typer(reset_app)
    app.add_typer(solve_app)
    app.add_typer(plugin_app, name="plugin")

    app()
