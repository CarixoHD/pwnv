import typer
from pwnv.models import CTF, Challenge
from pwnv.models.ctf import Status
from pwnv.models.challenge import Solved, Category
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
    add_challenge,
)
from InquirerPy import inquirer


from ctfbridge.utils.platform_detection import detect_platform
from ctfbridge import get_client
from ctfbridge.clients.ctfd_client import CTFdClient
from ctfbridge.clients.rctf_client import RCTFClient


app = typer.Typer(no_args_is_help=True)


@app.command()
@config_exists()
def add(
    name: str,
):
    ctfs = get_ctfs()

    path = (get_ctfs_path() / name).resolve()
    if is_duplicate(path=path, model_list=ctfs):
        print(f"[red]:x: Error:[/] CTF with name {name} or path {path} already exists.")
        return

    ctf = CTF(name=name, path=path)

    ctfs.append(ctf)
    config = read_config()
    config["ctfs"] = [ctf.model_dump() for ctf in ctfs]
    write_config(config)
    path.mkdir(parents=True, exist_ok=True)
    print(
        f"[green]:tada: Success![/] Added CTF [medium_spring_green]{name}[/] at [medium_spring_green]{path}[/]."
    )

    fetch_challenges = confirm(
        f"Do you want to fetch challenges from {ctf.name}?",
        default=True,
    )
    if not fetch_challenges:
        return
    url = inquirer.text(
        message="Enter the URL of the CTF (e.g. https://ctf.example.com)",
    ).execute()
    if not url:
        print("[red]:x: Error:[/] URL cannot be NONE.")
        return

    client = get_client(url)
    if not client:
        print("[red]:x: Error:[/] Failed to get CTF client.")
        return

    platform = detect_platform(url)
    if platform == "CTFd":
        client = CTFdClient(url)
        username = inquirer.text(
            message="Enter your CTFd username",
        ).execute()
        password = inquirer.text(
            message="Enter your CTFd password",
        ).execute()

        try:
            client.login(username, password)
        except Exception as e:
            print(f"[red]:x: Error:[/] Failed to login to CTFd: {e}")
            return
    elif platform == "rCTF":
        client = RCTFClient(url)
        token = inquirer.text(
            message="Enter your team token",
        ).execute()
        try:
            client.login("a", "A", token)
        except Exception as e:
            print(f"[red]:x: Error:[/] Failed to login to rCTF: {e}")
            return
    else:
        print(f"[red]:x: Error:[/] Unsupported platform: {platform}")
        return
    challenges = client.get_challenges()
    if not challenges:
        print("[red]:x: Error:[/] No challenges found.")
        return

    for challenge in challenges:
        try:
            category = Category[challenge.category.lower()]
        except KeyError:
            category = Category.other

        challenge.name = challenge.name.replace(" ", "-").lower()
        extras = {
            "description": challenge.description,
            "attachments": challenge.attachments,
        }

        new_challenge = Challenge(
            ctf_id=ctf.id,
            name=challenge.name,
            path=path / challenge.name,
            category=category,
            points=challenge.value,
            solved=Solved.solved if challenge.solved else Solved.unsolved,
            extras=extras,
        )

        add_challenge(new_challenge)
        print(
            f"[green]:tada: Success![/] Added challenge [medium_spring_green]{challenge.name}[/] to CTF [medium_spring_green]{ctf.name}[/]."
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


def show_ctf(ctf: CTF):
    print(f"[blue]{escape('[' + ctf.name + ']')}[/]")
    print(f"[red]path[/] = '{str(ctf.path)}'")
    print(f"[red]running[/] = '{str(ctf.running.name)}'")
    print(f"[red]date[/] = '{str(ctf.created_at.date())}'")
    print(
        f"[red]num_challenges[/] = {str(len(list(filter(lambda challenge: challenge.ctf_id == ctf.id, get_challenges()))))}"
    )
