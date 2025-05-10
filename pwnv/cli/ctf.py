import typer
from pwnv.models import CTF
from pwnv.models.ctf import Status
import shutil
from rich import print
from rich.markup import escape
from pwnv.cli.utils import (
    config_exists,
    get_ctfs,
    read_config,
    write_config,
    is_duplicate,
    get_challenges,
    get_current_ctf,
    select_ctf,
    confirm,
    get_ctfs_path,
    add_ctf,
    fetch_and_add_remote,
)
from InquirerPy import inquirer
from typing import Annotated

from ctfbridge import get_client
from ctfbridge.clients import RCTFClient

app = typer.Typer(no_args_is_help=True)


@app.command()
@config_exists()
def add(name: str):
    ctfs = get_ctfs()
    path = (get_ctfs_path() / name).resolve()
    if is_duplicate(path=path, model_list=ctfs):
        print(f"[red]:x: Error:[/] CTF '{name}' or path '{path}' already exists.")
        return

    fetch_challenges = confirm(
        f"Do you want to fetch challenges from '{name}'?", default=True
    )
    if fetch_challenges:
        url = (
            inquirer.text(
                message="Enter the URL of the CTF (e.g. https://ctf.example.com)"
            )
            .execute()
            .strip()
        )
        if not url:
            print("[red]:x: Error:[/] URL cannot be empty.")
            return

    creds = dict()
    client = None
    if fetch_challenges:
        try:
            client = get_client(url)
            if not client:
                raise RuntimeError("client initialization returned None")
        except Exception:
            print("[red]:x: Error:[/] Failed to get CTF client")
            return

        if isinstance(client, RCTFClient):
            creds["token"] = inquirer.text(message="Enter team token").execute().strip()
        else:
            creds["username"] = (
                inquirer.text(message="Enter your username").execute().strip()
            )
            creds["password"] = (
                inquirer.text(message="Enter your password", password=True)
                .execute()
                .strip()
            )
        if fetch_and_add_remote(
            ctf_name=name,
            url=url,
            username=creds.get("username"),
            password=creds.get("password"),
            token=creds.get("token"),
        ):
            print(
                f"[green]:tada: Success![/] Fetched CTF [medium_spring_green]{name}[/] from [medium_spring_green]{url}[/]."
            )
            return
        else:
            print(
                f"[red]:x: Error:[/] Failed to fetch CTF [medium_spring_green]{name}[/] from [medium_spring_green]{url}[/]."
            )
            return

    else:
        ctf = CTF(
            name=name,
            path=path,
            url="",
            username="",
            password="",
            token="",
        )
        add_ctf(ctf)
        print(
            f"[green]:tada: Success![/] Added CTF [medium_spring_green]{name}[/] at [medium_spring_green]{ctf.path}[/]."
        )


@app.command()
@config_exists()
def remove():
    ctfs = get_ctfs()
    if not ctfs:
        print("[red]:x: Error:[/] No CTFs found.")
        return

    chosen_ctf = select_ctf(ctfs, "Select a CTF to remove:")
    if not confirm(
        f"Are you sure you want to remove CTF {chosen_ctf.name} and all its challenges?",
        default=False,
    ):
        return

    challenges = get_challenges()
    challenges = list(
        filter(lambda challenge: challenge.ctf_id != chosen_ctf.id, challenges)
    )

    ctfs.remove(chosen_ctf)

    shutil.rmtree(chosen_ctf.path)

    config = read_config()
    config["ctfs"] = [ctf.model_dump() for ctf in ctfs]
    config["challenges"] = [challenge.model_dump() for challenge in challenges]
    write_config(config)

    print(
        f"[green]:tada: Success![/] Removed CTF [medium_spring_green]{chosen_ctf.name}[/]."
    )


@app.command()
@config_exists()
def info():
    ctfs = get_ctfs()
    if not ctfs:
        print("[red]:x: Error:[/] No CTFs found.")
        return

    while True:
        ctf = select_ctf(ctfs, "Select a CTF to view:")
        show_ctf(ctf)
        input("Press Enter to continue...")


@app.command()
@config_exists()
def stop():
    ctfs = get_ctfs()
    running_ctfs = list(filter(lambda ctf: ctf.running, ctfs))
    if not running_ctfs:
        print("[red]:x: Error:[/] No CTFs found.")
        return

    ctf = get_current_ctf(running_ctfs)
    if ctf and ctf.running:
        chosen_ctf = ctf
    else:
        chosen_ctf = select_ctf(running_ctfs, "Select a CTF to stop:")

    index = ctfs.index(chosen_ctf)
    chosen_ctf.running = Status.stopped
    ctfs[index] = chosen_ctf

    config = read_config()
    config["ctfs"] = [ctf.model_dump() for ctf in ctfs]
    write_config(config)
    print(
        f"[green]:tada: Success![/] Stopped CTF [medium_spring_green]{chosen_ctf.name}[/]."
    )


@app.command()
@config_exists()
def start():
    ctfs = get_ctfs()
    stopped_ctfs = list(filter(lambda ctf: not ctf.running, ctfs))
    if not stopped_ctfs:
        print("[red]:x: Error:[/] No stopped CTFs found.")
        return

    ctf = get_current_ctf(stopped_ctfs)
    if ctf:
        chosen_ctf = ctf
    else:
        chosen_ctf = select_ctf(stopped_ctfs, "Select a CTF to start:")

    index = ctfs.index(chosen_ctf)
    chosen_ctf.running = Status.running
    ctfs[index] = chosen_ctf

    config = read_config()
    config["ctfs"] = [ctf.model_dump() for ctf in ctfs]
    write_config(config)

    print(
        f"[green]:tada: Success![/] Started CTF [medium_spring_green]{chosen_ctf.name}[/]."
    )


@app.command()
@config_exists()
def fetch(
    name: str,
    url: str,
    username: Annotated[str, typer.Option(help="Username for the CTF")] = None,
    password: Annotated[str, typer.Option(help="Password for the CTF")] = None,
    token: Annotated[str, typer.Option(help="Token for the CTF")] = None,
):
    if is_duplicate(name=name, model_list=get_ctfs()):
        print(f"[red]:x: Error:[/] CTF '{name}' already exists.")
        return

    if (not username and not password) and not token:
        print(
            "[red]:x: Error:[/] Please provide either username and password or token."
        )
        return

    if fetch_and_add_remote(
        ctf_name=name,
        url=url,
        username=username,
        password=password,
        token=token,
    ):
        print(
            f"[green]:tada: Success![/] Fetched CTF [medium_spring_green]{name}[/] from [medium_spring_green]{url}[/]."
        )
    else:
        print(
            f"[red]:x: Error:[/] Failed to fetch CTF [medium_spring_green]{name}[/] from [medium_spring_green]{url}[/]."
        )
        return


def show_ctf(ctf: CTF):
    print(f"[blue]{escape('[' + ctf.name + ']')}[/]")
    print(f"[red]path[/] = '{str(ctf.path)}'")
    print(f"[red]running[/] = '{str(ctf.running.name)}'")
    print(f"[red]date[/] = '{str(ctf.created_at.date())}'")
    print(
        f"[red]num_challenges[/] = {str(len(list(filter(lambda challenge: challenge.ctf_id == ctf.id, get_challenges()))))}"
    )
