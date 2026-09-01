"""pwnv - a workspace manager for CTFs.

Both public names are resolved on demand. A solve script asks for
``from pwnv import challenge``, and assembling the Typer app to answer that
would import every command module - typer, rich and InquirerPy - for an object
that needs none of them.

``challenge`` is resolved when it is imported, from the working directory, and
is an ordinary :class:`ctfbridge.models.challenge.Challenge` afterwards. Call
:func:`pwnv.api.current` again if the directory changes under you.
"""

from typing import TYPE_CHECKING, Any, List

if TYPE_CHECKING:
    import typer

__all__ = ["app", "challenge", "main"]

_app: "typer.Typer | None" = None


def _build_app() -> "typer.Typer":
    import typer

    from pwnv.cli import (
        challenge_app,
        ctf_app,
        doctor_app,
        init_app,
        plugin_app,
        reset_app,
        shell_app,
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
    app.add_typer(shell_app)
    app.add_typer(solve_app)
    app.add_typer(status_app)
    app.add_typer(plugin_app, name="plugin")
    app.add_typer(workspace_app, name="workspace")
    return app


def _get_app() -> "typer.Typer":
    global _app

    if _app is None:
        _app = _build_app()
    return _app


def __getattr__(name: str) -> Any:
    if name == "app":
        return _get_app()
    if name == "challenge":
        from pwnv.api import current

        return current()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> List[str]:
    return sorted(__all__)


def main() -> None:
    """Entry point for the ``pwnv`` console script."""
    _get_app()()
