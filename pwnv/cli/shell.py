import typer

app = typer.Typer(no_args_is_help=True)

_POSIX_INIT = """\
pwncd() {
    local target
    target="$(command pwnv challenge path "$@")" || return $?
    [ -n "$target" ] || return 1
    cd "$target" || return $?
}
"""

_FISH_INIT = """\
function pwncd --description 'cd into a pwnv challenge'
    set -l target (command pwnv challenge path $argv)
    or return $status
    test -n "$target"
    or return 1
    cd $target
end
"""

_INIT_BY_SHELL = {
    "bash": _POSIX_INIT,
    "zsh": _POSIX_INIT,
    "sh": _POSIX_INIT,
    "fish": _FISH_INIT,
}


@app.command(name="shell-init")
def shell_init(
    shell: str | None = typer.Option(
        None, "--shell", help="bash, zsh, or fish (default: taken from $SHELL)"
    ),
) -> None:
    """
    Prints the shell functions that add `pwncd` to your session. Add
    `eval "$(pwnv shell-init)"` to your shell's rc file, or
    `pwnv shell-init | source` for fish.
    """
    import os
    from pathlib import Path

    from pwnv.utils import error

    name = (shell or Path(os.environ.get("SHELL", "bash")).name).lower()
    script = _INIT_BY_SHELL.get(name)
    if script is None:
        supported = ", ".join(sorted(_INIT_BY_SHELL))
        error(f"Unsupported shell '{name}'. Supported: {supported}.")
        raise typer.Exit(code=1)

    typer.echo(script, nl=False)
