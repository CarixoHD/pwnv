from typing import List, Sequence

from rich.markup import escape

from pwnv.models import CTF, Challenge
from pwnv.models.challenge import Category, Solved
from pwnv.plugins import ChallengePlugin
from pwnv.utils.crud import challenges_for_ctf, get_ctfs, get_tags


def success(msg: str):
    from rich import print

    print(f"[green]✓[/] {msg}")


def error(msg: str):
    from rich import print

    print(f"[red]error:[/] {msg}")


def warn(msg: str):
    from rich import print

    print(f"[yellow]warning:[/] {msg}")


def info(msg: str):
    from rich import print

    print(f"[blue]info:[/] {msg}")


def command(msg: str):
    return f"[cyan]`{msg}`[/]"


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

    return [
        Choice(
            name=f"{plugin.__module__:<50} [{plugin.category().name}]",
            value=plugin,
        )
        for plugin in plugins
    ]


def prompt_confirm(message: str, default: bool = True, **kwargs):
    from InquirerPy import inquirer

    return inquirer.confirm(message=message, default=default, **kwargs).execute()


def prompt_fuzzy_select(
    *,
    choices,
    message: str = "Select:",
    **kwargs,
):
    from InquirerPy import inquirer

    return inquirer.fuzzy(
        message=message, choices=list(choices), border=True, **kwargs
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


def prompt_category_selection() -> Category:
    category = prompt_fuzzy_select(
        choices=[c.name for c in Category], message="Select category:"
    )
    return Category[category]


def prompt_tags_selection(msg: str) -> List[str]:
    return prompt_fuzzy_select(choices=list(get_tags()), message=msg, multiselect=True)


def prompt_text(msg: str, **kwargs) -> str:
    from InquirerPy import inquirer

    return inquirer.text(message=msg, **kwargs).execute().strip()


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

    from pwnv.utils.plugin import get_plugin_selection, get_plugins_directory

    plugins_dir = get_plugins_directory()
    selection = get_plugin_selection()

    name = plugin.__module__
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
