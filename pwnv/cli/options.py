"""Options shared by more than one command."""

import typer

JSON = typer.Option(
    False,
    "--json",
    help="Print the result as JSON on stdout instead of a rendered view",
)
"""Ask a read command for data rather than a display.

Declared once so every command spells the flag the same way, and so the
contract stays visible: JSON goes to stdout, nothing else does, and a command
in this mode never opens a picker - there is no one to answer it.
"""
