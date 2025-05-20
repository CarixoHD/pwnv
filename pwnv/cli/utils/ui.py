from typing import List, Sequence, Union

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich import print
from rich.markup import escape

from pwnv.cli.utils.crud import get_challenges, get_ctfs, get_tags
from pwnv.models import CTF, Challenge
from pwnv.models.challenge import Category, Solved


def success(msg: str):
    print(f"[green]✓[/] {msg}")


def error(msg: str):
    print(f"[red]Error:[/] {msg}")


def warn(msg: str):
    print(f"[yellow]Warning:[/] {msg}")


_BasicChoice = Union[CTF, Challenge]


def _get_challenge_choices(challenges: Sequence[Challenge]) -> List[Choice]:
    ctf_names = {ctf.id: ctf.name for ctf in get_ctfs()}
    return [
        Choice(
            name=f"{ch.name:<50} [{ctf_names[ch.ctf_id]}][{'solved' if ch.solved == Solved.solved else 'unsolved'}][{ch.category.name}]",
            value=ch,
        )
        for ch in challenges
    ]


def _get_ctf_choices(ctfs: Sequence[CTF]) -> List[Choice]:
    return [
        Choice(name=f"{ctf.name:<50} [{ctf.created_at.year}]", value=ctf)
        for ctf in ctfs
    ]


def confirm(message: str, default: bool = True, **kwargs):
    return inquirer.confirm(message=message, default=default, **kwargs).execute()


def fuzzy_select(
    *,
    choices: Sequence[_BasicChoice | Choice | str],
    message: str = "Select:",
    **kwargs,
):
    return inquirer.fuzzy(
        message=message, choices=list(choices), border=True, **kwargs
    ).execute()


def prompt_challenge_selection(challenges: Sequence[Challenge], msg: str) -> Challenge:
    return fuzzy_select(
        choices=_get_challenge_choices(challenges),
        message=msg,
        transformer=lambda r: r.split(" ")[0],
    )


def prompt_ctf_selection(ctfs: Sequence[CTF], msg: str) -> CTF:
    return fuzzy_select(
        choices=_get_ctf_choices(ctfs),
        message=msg,
        transformer=lambda r: r.split(" ")[0],
    )


def prompt_category_selection() -> Category:
    category = fuzzy_select(
        choices=[c.name for c in Category], message="Select category:"
    )
    return Category[category]


def prompt_tags_selection(msg: str) -> List[str]:
    return fuzzy_select(choices=list(get_tags()), message=msg, multiselect=True)


def prompt_text(msg: str) -> str:
    return inquirer.text(message=msg).execute().strip()


def show_challenge(challenge: Challenge):
    print(f"[blue]{escape('[' + challenge.name + ']')}[/]")
    print(
        f"[red]ctf[/] = '{list(filter(lambda ctf: ctf.id == challenge.ctf_id, get_ctfs()))[0].name}'"
    )
    print(f"[red]category[/] = '{challenge.category.name}'")
    print(f"[red]path[/] = '{str(challenge.path)}'")
    print(f"[red]solved[/] = '{str(challenge.solved.name)}'")
    print(f"[red]points[/] = '{str(challenge.points)}'")
    print(f"[red]flag[/] = '{str(challenge.flag)}'")
    print(f"[red]tags[/] = '{', '.join(challenge.tags) if challenge.tags else ''}'")


def show_ctf(ctf: CTF):
    print(f"[blue]{escape('[' + ctf.name + ']')}[/]")
    print(f"[red]path[/] = '{str(ctf.path)}'")
    print(f"[red]running[/] = '{str(ctf.running.name)}'")
    print(f"[red]date[/] = '{str(ctf.created_at.date())}'")
    print(
        f"[red]num_challenges[/] = {str(len(list(filter(lambda challenge: challenge.ctf_id == ctf.id, get_challenges()))))}"
    )
