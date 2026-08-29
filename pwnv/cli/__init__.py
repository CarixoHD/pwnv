from pwnv.cli.challenge import app as challenge_app
from pwnv.cli.challenge_env import app as challenge_env_app
from pwnv.cli.ctf import app as ctf_app
from pwnv.cli.doctor import app as doctor_app
from pwnv.cli.init import app as init_app
from pwnv.cli.note import app as note_app
from pwnv.cli.plugin import app as plugin_app
from pwnv.cli.reset import app as reset_app
from pwnv.cli.solve import app as solve_app
from pwnv.cli.status import app as status_app
from pwnv.cli.workspace import app as workspace_app

challenge_app.add_typer(challenge_env_app, name="env")
challenge_app.add_typer(note_app, name="note")

__all__ = [
    "challenge_app",
    "ctf_app",
    "doctor_app",
    "init_app",
    "reset_app",
    "solve_app",
    "status_app",
    "plugin_app",
    "workspace_app",
]
