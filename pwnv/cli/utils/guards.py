from functools import wraps

from pwnv.cli.utils.config import config_path
from pwnv.cli.utils.crud import get_challenges, get_ctfs
from pwnv.cli.utils.ui import warn


def _guard(predicate, msg):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if predicate():
                return fn(*a, **kw)
            warn(msg)

        return wrapper

    return deco


def config_exists():
    return _guard(
        lambda: config_path.exists(),
        "No config. Run [magenta]`pwnv init`[/]. ",
    )


def ctfs_exists():
    return _guard(lambda: bool(get_ctfs()), "No CTFs found.")


def challenges_exists():
    return _guard(lambda: bool(get_challenges()), "No challenges found.")
