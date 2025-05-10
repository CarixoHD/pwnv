import typer
import shutil
from rich import print
from pwnv.cli.utils import (
    config_exists,
    confirm,
    get_ctfs_path,
    get_config,
)


app = typer.Typer(no_args_is_help=True)


@app.command()
@config_exists()
def reset():
    if not confirm("Are you sure you want to reset the environment?"):
        return

    env_path = get_ctfs_path()
    if confirm("Do you wish to delete all the CTF and challenge files?"):
        shutil.rmtree(env_path)
    print(f"[green]:white_check_mark: Environment at {env_path} has been deleted.[/]")

    # # config = read_config()
    #     for challenge in get_challenges():
    #         shutil.rmtree(challenge.path)
    #     for ctf in get_ctfs():
    #         shutil.rmtree(ctf.path)
    print("[green]:white_check_mark: All CTF and challenge files have been deleted.[/]")

    get_config().unlink()
    print("[green]:white_check_mark: Environment has been reset.[/]")
    print("[green]:white_check_mark: Run `pwnv init` to create a new environment.[/]")
