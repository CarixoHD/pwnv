from pwnv.cli import challenge_app, ctf_app, init_app

import typer


def main():
    app = typer.Typer(no_args_is_help=True)
    app.add_typer(challenge_app, name="challenge")
    app.add_typer(ctf_app, name="ctf", invoke_without_command=True)
    app.add_typer(init_app)
    app()
