import typer

from pwnv.utils import (
    config_exists,
    plugins_exists,
)

app = typer.Typer(
    no_args_is_help=True, help="Manage pwnv plugins for different challenge categories."
)


@app.command()
@config_exists()
def add(name: str) -> None:
    """
    Creates a new plugin file and its associated template for a specific category.
    Use 'pwnv plugin select' to activate it.
    """
    import re

    from pwnv.constants import DEFAULT_TEMPLATE_FILENAME
    from pwnv.utils import (
        create_plugin_file,
        error,
        get_plugins_directory,
        get_templates_directory,
        info,
        prompt_category_selection,
        prompt_text,
        set_selected_plugin_for_category,
        success,
    )

    if not re.fullmatch(r"[a-zA-Z0-9]+", name) or not name.isidentifier():
        error(
            f"Invalid plugin name '{name}'."
            "Must be alphanumeric (no underscores, dashes, or spaces)."
        )
        return

    plugins_dir = get_plugins_directory()
    plugin_file = plugins_dir / f"{name}.py"

    if plugin_file.exists():
        error(f"Plugin '{name}' already exists at {plugin_file}.")
        return

    category = prompt_category_selection()
    templates_dir = get_templates_directory() / category.name
    templates_dir.mkdir(parents=True, exist_ok=True)

    template_name = prompt_text(
        "Enter the default template filename:", default=DEFAULT_TEMPLATE_FILENAME
    )
    user_tpl = templates_dir / template_name
    if not user_tpl.exists():
        user_tpl.touch()

    create_plugin_file(plugin_file, name, category, template_name)
    set_selected_plugin_for_category(category, name)

    success(f"Plugin '{name}' created for category '{category.name}'.")
    info(f"Plugin file: {plugin_file}")
    info(f"Template file: {user_tpl}")


@app.command()
@config_exists()
@plugins_exists()
def remove() -> None:
    """
    Removes a selected plugin file and updates the plugin selection accordingly.
    """
    from pwnv.core import plugin_manager
    from pwnv.utils import (
        error,
        get_plugin_selection,
        get_plugins_directory,
        info,
        prompt_confirm,
        prompt_plugin_selection,
        save_plugin_selection,
        success,
        warn,
    )

    plugins = plugin_manager.get_all_plugins()
    if not plugins:
        warn("No plugins to remove.")
        return

    chosen_plugin = prompt_plugin_selection(plugins, "Select a plugin to remove:")

    plugin_name_lower = chosen_plugin.__module__
    plugins_dir = get_plugins_directory()
    plugin_file = plugins_dir / f"{plugin_name_lower}.py"

    if not plugin_file.exists():
        error(f"Plugin file '{plugin_file}' not found (this shouldn't happen).")
        return

    if not prompt_confirm(
        f"Are you sure you want to remove the plugin '{plugin_name_lower}' "
        f"({plugin_file})?",
        default=False,
    ):
        warn("Plugin removal aborted.")
        return

    try:
        plugin_file.unlink()
        success(f"Plugin file '{plugin_file}' removed.")

        selection = get_plugin_selection()
        updated = False
        keys_to_delete = []

        for cat_name, selected_plugin_name in selection.items():
            if selected_plugin_name == plugin_name_lower:
                keys_to_delete.append(cat_name)
                info(
                    f"Removed '{plugin_name_lower}'"
                    "as selected plugin for '{cat_name}'."
                )
                updated = True

        if updated:
            for key in keys_to_delete:
                del selection[key]
            save_plugin_selection(selection)

        info("Plugin removed.")

    except Exception as e:
        error(f"Failed to remove plugin '{plugin_name_lower}': {e}")


@app.command(name="info")
@config_exists()
@plugins_exists()
def info_() -> None:
    """
    Lists all available plugins and displays detailed information,
      including source code, for a selected plugin.
    """
    from pwnv.core import plugin_manager
    from pwnv.utils import (
        prompt_confirm,
        prompt_plugin_selection,
        show_plugin,
        warn,
    )

    plugins = plugin_manager.get_all_plugins()
    if not plugins:
        warn("No plugins found or loaded. Use 'pwnv plugin add' to create one.")
        return

    while True:
        chosen_plugin = prompt_plugin_selection(
            plugins, "Select a plugin to show info:"
        )
        show_plugin(chosen_plugin)

        if not prompt_confirm("Show another plugin?", default=False):
            break


@app.command()
@config_exists()
@plugins_exists()
def select() -> None:
    """
    Selects the active plugin to be used for a chosen challenge category.
    """
    from pwnv.core import plugin_manager
    from pwnv.utils import (
        error,
        prompt_category_selection,
        prompt_plugin_selection,
        set_selected_plugin_for_category,
        success,
    )

    category = prompt_category_selection()
    plugins_for_cat = plugin_manager.get_plugins_by_category(category)

    if not plugins_for_cat:
        error(
            f"No plugins found for the category '{category.name}'. "
            f"Use 'pwnv plugin add' to create one."
        )
        return

    chosen_plugin = prompt_plugin_selection(
        plugins_for_cat, f"Select a plugin for '{category.name}':"
    )

    if chosen_plugin:
        plugin_stem = chosen_plugin.__module__
        set_selected_plugin_for_category(category, plugin_stem)
        success(
            f"Plugin '{plugin_stem}' is now selected for the "
            f"'{category.name}' category."
        )
