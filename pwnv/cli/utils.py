from functools import wraps
from pathlib import Path
import typer
from rich import print
from pwnv.models import CTF, Challenge
from pwnv.models.challenge import Solved
import json
from typing import List
from InquirerPy import inquirer
from InquirerPy.base.control import Choice


config_path = Path(typer.get_app_dir("pwnv")) / "config.json"


def config_exists() -> bool:
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if config_path.exists():
                return func(*args, **kwargs)
            else:
                print(
                    "[bold red]:x: Error:[/] Config file does not exist. Run [cyan]`pwnv init`[/] to create one."
                )

        return wrapper

    return decorator


def ctfs_exists() -> bool:
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if get_ctfs():
                return func(*args, **kwargs)
            else:
                print("[bold red]:x: Error:[/] No CTFs found.")

        return wrapper

    return decorator


def read_config() -> dict:
    with open(config_path, "r") as f:
        return json.load(f)


def write_config(config: dict):
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4, default=str)


def get_ctfs() -> list[CTF]:
    config = read_config()
    return [CTF(**ctf) for ctf in config["ctfs"]]


def get_challenges() -> list[Challenge]:
    config = read_config()
    return [Challenge(**challenge) for challenge in config["challenges"]]


def get_tags() -> list[str]:
    config = read_config()
    return config["challenge_tags"]


def set_tags(tags: list[str]):
    config = read_config()
    config["challenge_tags"] = tags
    write_config(config)


def get_current_ctf(ctfs: List[CTF]) -> CTF:
    if any(ctf.path == Path.cwd() or ctf.path in Path.cwd().parents for ctf in ctfs):
        return next(
            ctf
            for ctf in ctfs
            if ctf.path == Path.cwd() or ctf.path in Path.cwd().parents
        )
    return []


def get_current_challenge(challenges: List[Challenge]) -> Challenge:
    if any(
        challenge.path == Path.cwd() or challenge.path in Path.cwd().parents
        for challenge in challenges
    ):
        return next(
            challenge
            for challenge in challenges
            if challenge.path == Path.cwd() or challenge.path in Path.cwd().parents
        )
    return []


def confirm(message: str, default: bool = True, *args, **kwargs):
    return inquirer.confirm(*args, **kwargs, message=message, default=default).execute()


def select(message: str, choices: List, *args, **kwargs):
    return inquirer.select(message=message, choices=choices, *args, **kwargs).execute()


def select_fuzzy(choices: List[CTF | Challenge], message: str) -> CTF | Challenge:
    if isinstance(choices[0], CTF):
        options = map(
            lambda choice: Choice(
                name=f"{choice.name:<50} ({choice.created_at.year})", value=choice
            ),
            sorted(choices, key=lambda ctf: ctf.created_at, reverse=True),
        )
    else:
        ctf_names = {ctf.id: ctf.name for ctf in get_ctfs()}
        options = map(
            lambda choice: Choice(
                name=f"{choice.name:<50} ({ctf_names[choice.ctf_id]})", value=choice
            ),
            choices,
        )
    return inquirer.fuzzy(
        message=message,
        choices=options,
        border=True,
    ).execute()


def fuzzy_select(*, choices: List[CTF | Challenge], **kwargs) -> CTF | Challenge:
    return inquirer.fuzzy(
        message=kwargs.pop("message", "Select an item:"),
        choices=choices,
        border=True,
        **kwargs,
    ).execute()


def select_challenge(challenges: List[Challenge], msg: str) -> Challenge:
    challenge = fuzzy_select(
        choices=get_challenge_choices(challenges),
        message=msg,
        transformer=lambda result: result.split(" ")[0],
    )
    return challenge


def select_ctf(ctfs: List[CTF], msg: str) -> CTF:
    ctf = fuzzy_select(
        choices=get_ctf_choices(ctfs),
        message=msg,
        transformer=lambda result: result.split(" ")[0],
    )
    return ctf


def select_tags(msg: str) -> List[str]:
    tags = get_tags()
    return fuzzy_select(
        choices=tags,
        message=msg,
        multiselect=True,
    )


def get_challenge_choices(challenges: List[Challenge]) -> List[Choice]:
    ctf_names = {ctf.id: ctf.name for ctf in get_ctfs()}
    options = map(
        lambda choice: Choice(
            name=f"{choice.name:<50} [{ctf_names[choice.ctf_id]}][{"solved" if choice.solved == Solved.solved else "unsolved"}]",
            value=choice,
        ),
        challenges,
    )
    return list(options)


def get_ctf_choices(ctfs: List[CTF]) -> List[Choice]:
    options = map(
        lambda choice: Choice(
            name=f"{choice.name:<50} [{choice.created_at.year}]", value=choice
        ),
        ctfs,
    )
    return list(options)


def is_duplicate(
    *,
    name: str | None = None,
    path: Path | None = None,
    model_list: List[CTF | Challenge],
) -> bool:
    if path is None:
        return any(model.name == name for model in model_list)
    elif name is None:
        return any(model.path == path for model in model_list)
    return any(model.name == name or model.path == path for model in model_list)
