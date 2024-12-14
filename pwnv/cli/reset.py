import typer
from typing import Annotated, Optional
from pwnv.models import CTF
from pwnv.models.ctf import Status
from pathlib import Path
import shutil
from rich import print
from rich.table import Table
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
    get_env_path,
    is_default_ctf_path,
)
from datetime import datetime


app = typer.Typer(no_args_is_help=True)


@app.command()
@config_exists()
def reset():
    if not confirm("Are you sure you want to reset the environment?"):
        return
    
    env_path = get_env_path()
    shutil.rmtree(env_path)
    print(f"[green]:white_check_mark: Environment at {env_path} has been deleted.[/]")
    
    #config = read_config()
    if confirm("Do you wish to delete all the CTF and challenge files?"):
        for challenge in get_challenges():
            shutil.rmtree(challenge.path)
        for ctf in get_ctfs():
            shutil.rmtree(ctf.path)
        print("[green]:white_check_mark: All CTF and challenge files have been deleted.[/]")
    
    
    
    config_path = Path(typer.get_app_dir("pwnv")) / "config.json"
    config_path.unlink()
    print("[green]:white_check_mark: Environment has been reset.[/]")
    print("[green]:white_check_mark: Run `pwnv init` to create a new environment.[/]")
    
    