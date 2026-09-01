from collections.abc import Generator
from contextlib import contextmanager
from typing import IO, TYPE_CHECKING, List, Sequence

from rich.markup import escape

from pwnv.models import CTF, Challenge
from pwnv.models.challenge import Category, Solved
from pwnv.plugins import ChallengePlugin
from pwnv.utils.crud import challenges_for_ctf, get_ctfs, get_tags

if TYPE_CHECKING:
    from rich.console import Console


_diagnostic_console: "Console | None" = None


def _diagnostics() -> "Console":
    """
    The console that notices, warnings and errors are written on.

    stdout is a data channel: ``pwncd`` expands to ``cd "$(pwnv challenge
    path)"`` and ``--json`` output gets piped into other tools, so a passing
    remark on stdout corrupts the result. Diagnostics go to stderr instead,
    where a human still sees them and a parser does not.

    ``stderr=True`` resolves ``sys.stderr`` on every write, so the redirect in
    :func:`prompt_on_tty` and the capture in tests both keep working.
    """
    global _diagnostic_console

    if _diagnostic_console is None:
        from rich.console import Console

        _diagnostic_console = Console(stderr=True)
    return _diagnostic_console


def success(msg: str):
    _diagnostics().print(f"[green]✓[/] {msg}")


def error(msg: str):
    _diagnostics().print(f"[red]error:[/] {msg}")


def warn(msg: str):
    _diagnostics().print(f"[yellow]warning:[/] {msg}")


def info(msg: str):
    _diagnostics().print(f"[blue]info:[/] {msg}")


def command(msg: str):
    return f"[cyan]`{msg}`[/]"


def debug_enabled() -> bool:
    """Report whether ``PWNV_DEBUG`` is set to something that means yes."""
    import os

    from pwnv.constants import PWNV_DEBUG_ENV

    return os.getenv(PWNV_DEBUG_ENV, "").strip().lower() not in ("", "0", "false", "no")


def debug_traceback() -> None:
    """
    Print the exception being handled, when ``PWNV_DEBUG`` is set.

    A command that swallows an exception to print a sentence instead is right
    for an event and useless for a bug report: "Failed to fetch challenges."
    says nothing about which platform call failed. Set ``PWNV_DEBUG=1`` to get
    the traceback alongside the sentence, on stderr with the other diagnostics.
    """
    import sys
    import traceback

    if not debug_enabled() or sys.exc_info()[0] is None:
        return
    _diagnostics().print("[dim]" + escape(traceback.format_exc().rstrip()) + "[/]")


def _get_challenge_choices(challenges: Sequence[Challenge]):
    from InquirerPy.base.control import Choice

    ctf_names = {ctf.id: ctf.name for ctf in get_ctfs()}
    return [
        Choice(
            name=f"{ch.name:<50} [{ctf_names[ch.ctf_id]}]["
            f"{'solved' if ch.solved == Solved.solved else 'unsolved'}]"
            f"[{ch.category.name}]",
            value=ch,
        )
        for ch in challenges
    ]


def _get_ctf_choices(ctfs: Sequence[CTF]):
    from InquirerPy.base.control import Choice

    return [
        Choice(name=f"{ctf.name:<50} [{ctf.created_at.year}]", value=ctf)
        for ctf in ctfs
    ]


def _get_plugin_choices(plugins: Sequence[ChallengePlugin]):
    from InquirerPy.base.control import Choice

    from pwnv.core.plugin_manager import plugin_name

    return [
        Choice(
            name=f"{plugin_name(plugin):<50} [{plugin.category().name}]",
            value=plugin,
        )
        for plugin in plugins
    ]


_stdout_is_captured = False


@contextmanager
def prompt_on_tty() -> Generator[IO[str]]:
    """
    Route prompts and messages to the terminal, yielding the untouched stdout.

    ``pwncd`` expands to ``cd "$(pwnv challenge path)"``, so stdout is a pipe. A
    selector drawn there would be captured instead of displayed and the shell
    would look like it hung, so the interface goes to the tty and only the
    answer is written to stdout.
    """
    global _stdout_is_captured

    import contextlib
    import sys

    real_stdout = sys.stdout
    previous = _stdout_is_captured
    _stdout_is_captured = True
    try:
        with contextlib.redirect_stdout(sys.stderr):
            yield real_stdout
    finally:
        _stdout_is_captured = previous


@contextmanager
def _prompt_session() -> Generator[None]:
    """
    Draw the next prompt on the terminal when stdout has been captured.

    Claiming the tty is deferred until something actually prompts: doing it up
    front makes prompt_toolkit complain about a non-interactive stdin on every
    `pwncd`, which resolves without asking anything most of the time.
    """
    import contextlib

    if not _stdout_is_captured:
        yield
        return

    from prompt_toolkit.application import create_app_session_from_tty

    with contextlib.ExitStack() as stack:
        with contextlib.suppress(Exception):
            stack.enter_context(create_app_session_from_tty())
        yield


def prompt_confirm(message: str, default: bool = True, **kwargs):
    from InquirerPy import inquirer

    with _prompt_session():
        return inquirer.confirm(message=message, default=default, **kwargs).execute()


def prompt_fuzzy_select(
    *,
    choices,
    message: str = "Select:",
    **kwargs,
):
    import typer
    from InquirerPy import inquirer

    options = list(choices)
    if not options:
        error("Nothing to select from.")
        raise typer.Exit(code=1)

    with _prompt_session():
        return inquirer.fuzzy(
            message=message, choices=options, border=True, **kwargs
        ).execute()


def prompt_challenge_selection(challenges: Sequence[Challenge], msg: str) -> Challenge:
    return prompt_fuzzy_select(
        choices=_get_challenge_choices(challenges),
        message=msg,
        transformer=lambda r: r.split(" ")[0],
    )


def prompt_ctf_selection(ctfs: Sequence[CTF], msg: str) -> CTF:
    return prompt_fuzzy_select(
        choices=_get_ctf_choices(ctfs),
        message=msg,
        transformer=lambda r: r.split(" ")[0],
    )


def prompt_plugin_selection(
    plugins: Sequence[ChallengePlugin], msg: str, **kwargs
) -> ChallengePlugin:
    return prompt_fuzzy_select(
        choices=_get_plugin_choices(plugins),
        message=msg,
        transformer=lambda r: r.split(" ")[0],
        **kwargs,
    )


def prompt_category_selection(default: Category | None = None) -> Category:
    category = prompt_fuzzy_select(
        choices=[c.name for c in Category],
        message="Select category:",
        default=default.name if default else "",
    )
    return Category[category]


def prompt_tags_selection(msg: str) -> List[str]:
    return prompt_fuzzy_select(choices=list(get_tags()), message=msg, multiselect=True)


def prompt_text(msg: str, **kwargs) -> str:
    from InquirerPy import inquirer

    with _prompt_session():
        return inquirer.text(message=msg, **kwargs).execute().strip()


def format_service(service: dict) -> str:
    """Render one fetched service as the string you would actually connect with."""
    if not isinstance(service, dict):
        return str(service)
    if service.get("url"):
        return str(service["url"])
    host, port = service.get("host"), service.get("port")
    if host and port:
        return f"nc {host} {port}"
    return str(host or service.get("raw") or "")


def render_sync_summary(ctf_name: str, summary: dict, *, quiet: bool = False) -> None:
    """
    Print what a sync changed rather than replaying the whole scoreboard.

    During a live event the interesting part is the delta: what unlocked, what
    got repriced by dynamic scoring, and what a teammate already solved.
    """
    from rich import print

    added = summary.get("added") or []
    updated = summary.get("updated") or []
    unchanged = summary.get("unchanged") or 0

    if not added and not updated:
        if not quiet:
            info(f"{ctf_name}: no changes ({unchanged} challenges up to date).")
        return

    print(f"[blue]{escape('[' + ctf_name + ']')}[/]")
    for name in added:
        print(f"  [green]+[/] {escape(str(name))}")
    for item in updated:
        changes = escape(", ".join(str(change) for change in item.get("changes", [])))
        print(f"  [yellow]~[/] {escape(str(item.get('name')))} [dim]({changes})[/]")

    tail = [f"{unchanged} unchanged"]
    if downloaded := summary.get("attachments_downloaded"):
        tail.append(f"{len(downloaded)} attachment set(s) downloaded")
    if reused := summary.get("attachments_reused"):
        tail.append(f"{len(reused)} already on disk")
    print(f"  [dim]{', '.join(tail)}[/]")


def show_challenge(challenge: Challenge):
    from rich import print

    print(f"[blue]{escape('[' + challenge.name + ']')}[/]")
    ctf = next(ctf for ctf in get_ctfs() if ctf.id == challenge.ctf_id)
    print(f"[red]ctf[/] = '{ctf.name}'")
    print(f"[red]category[/] = '{challenge.category.name}'")
    print(f"[red]path[/] = '{str(challenge.path)}'")
    print(f"[red]solved[/] = '{str(challenge.solved.name)}'")
    print(f"[red]points[/] = '{str(challenge.points)}'")
    print(f"[red]flag[/] = '{str(challenge.flag)}'")
    print(f"[red]tags[/] = '{', '.join(challenge.tags) if challenge.tags else ''}'")

    extras = challenge.extras if isinstance(challenge.extras, dict) else {}
    if author := extras.get("author"):
        print(f"[red]author[/] = '{escape(str(author))}'")

    services = extras.get("services") or []
    if isinstance(services, list) and services:
        rendered = [format_service(svc) for svc in services]
        print(f"[red]service[/] = '{escape(', '.join(s for s in rendered if s))}'")

    attachments = extras.get("attachments") or []
    if isinstance(attachments, list) and attachments:
        names = [
            str(att.get("name") or att.get("url") or "")
            for att in attachments
            if isinstance(att, dict)
        ]
        print(f"[red]attachments[/] = '{escape(', '.join(n for n in names if n))}'")

    if description := extras.get("description"):
        print(f"[red]description[/] =\n{escape(str(description).strip())}")


def show_ctf(ctf: CTF):
    from rich import print

    print(f"[blue]{escape('[' + ctf.name + ']')}[/]")
    print(f"[red]path[/] = '{str(ctf.path)}'")
    print(f"[red]running[/] = '{str(ctf.running.name)}'")
    print(f"[red]date[/] = '{str(ctf.created_at.date())}'")
    print(f"[red]num_challenges[/] = {len(challenges_for_ctf(ctf))}")


def show_plugin(plugin: ChallengePlugin):
    from rich import print
    from rich.panel import Panel
    from rich.syntax import Syntax

    from pwnv.core.plugin_manager import plugin_name
    from pwnv.utils.plugin import get_plugin_selection, get_plugins_directory

    plugins_dir = get_plugins_directory()
    selection = get_plugin_selection()

    name = plugin_name(plugin)
    category = plugin.category().name
    file_path = plugins_dir / f"{name}.py"
    is_selected = selection.get(category) == name

    print(f"\n[blue]{escape('[' + name + ']')}[/]")
    print(f"[red]category[/] = '{category}'")
    print(f"[red]file[/] = '{str(file_path)}'")
    print(f"[red]selected[/] = '{'Yes' if is_selected else 'No'}'")
    if file_path.exists():
        try:
            code = file_path.read_text(encoding="utf-8")
            syntax = Syntax(
                code,
                "python",
                theme="monokai",
                line_numbers=True,
                background_color="default",
            )
            print(
                Panel(
                    syntax,
                    title=f"Source Code ({file_path.name})",
                    border_style="green",
                    expand=True,
                )
            )
        except Exception as e:
            warn(f"Could not read or display source code: {e}")
    else:
        warn("Source code file not found.")
    print("-" * 60)
