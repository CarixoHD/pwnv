from functools import wraps


def _guard(predicate, msg):
    from pwnv.cli.utils.ui import warn

    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if predicate():
                return fn(*a, **kw)
            warn(msg)

        return wrapper

    return deco


def config_exists():
    from pwnv.cli.utils.config import get_config_path
    from pwnv.cli.utils.ui import command

    return _guard(
        lambda: get_config_path().exists(),
        f"No config. Run {command('pwnv init')}. ",
    )


def ctfs_exists():
    from pwnv.cli.utils.crud import get_ctfs

    return _guard(lambda: bool(get_ctfs()), "No CTFs found.")


def challenges_exists():
    from pwnv.cli.utils.crud import get_challenges

    return _guard(lambda: bool(get_challenges()), "No challenges found.")
