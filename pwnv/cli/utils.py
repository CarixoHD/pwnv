from functools import wraps
from pathlib import Path
import typer
from rich import print
from pwnv.models import CTF, Challenge
import json
from typing import List
from InquirerPy import inquirer
from InquirerPy.base.control import Choice


config_path = Path(typer.get_app_dir("pwnv")) / "config.json"


def get_challenge_by_id(id: int, json: dict) -> dict:
    for challenge in json["challenges"]:
        if challenge["id"] == id:
            return challenge
    return None


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


def select_fuzzy(choices: List[CTF | Challenge], message: str) -> CTF | Challenge:
    if isinstance(choices[0], CTF):
        options = map(
            lambda choice: Choice(
                name=f"{choice.name:<50} ({choice.created_at.year})", value=choice
            ),
            choices,
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
    ).execute()


def confirm(message: str) -> bool:
    return typer.confirm(message, default=True)


def is_duplicate(
    name: str | None, path: Path | None, model_list: List[CTF | Challenge]
) -> bool:
    if path is None:
        return any(model.name == name for model in model_list)
    elif name is None:
        return any(model.path == path for model in model_list)
    return any(model.name == name or model.path == path for model in model_list)
