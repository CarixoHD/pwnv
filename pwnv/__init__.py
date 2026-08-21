import typer

from pwnv.cli import (
    challenge_app,
    ctf_app,
    doctor_app,
    init_app,
    plugin_app,
    reset_app,
    solve_app,
    status_app,
    workspace_app,
)

app = typer.Typer()
app.add_typer(challenge_app, name="challenge")
app.add_typer(ctf_app, name="ctf")
app.add_typer(doctor_app)
app.add_typer(init_app)
app.add_typer(reset_app)
app.add_typer(solve_app)
app.add_typer(status_app)
app.add_typer(plugin_app, name="plugin")
app.add_typer(workspace_app, name="workspace")


def main():
    app()
