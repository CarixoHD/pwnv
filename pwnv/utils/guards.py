def _guard(predicate, msg, *, empty_is_data=False):
    from functools import wraps

    import typer

    from pwnv.utils.ui import warn

    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if predicate() or (empty_is_data and kw.get("json_output")):
                return fn(*a, **kw)
            warn(msg)
            raise typer.Exit(code=1)

        return wrapper

    return deco


def config_exists():
    from pwnv.utils.config import get_config_path
    from pwnv.utils.ui import command

    return _guard(
        lambda: get_config_path().exists(),
        f"No config found. Run {command('pwnv init')}. ",
    )


def ctfs_exists():
    from pwnv.utils.crud import get_ctfs

    return _guard(lambda: bool(get_ctfs()), "No CTFs found.", empty_is_data=True)


def challenges_exists():
    from pwnv.utils.crud import get_challenges

    return _guard(
        lambda: bool(get_challenges()), "No challenges found.", empty_is_data=True
    )


def plugins_exists():
    def _any_plugins() -> bool:
        from pwnv.core import plugin_manager

        return bool(plugin_manager.get_all_plugins())

    return _guard(_any_plugins, "No plugins found or loaded.", empty_is_data=True)
