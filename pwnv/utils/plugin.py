from pathlib import Path
from typing import Dict, List

from pwnv.constants import (
    DEFAULT_EXAMPLES_FOLDER_NAME,
    DEFAULT_PLUGINS_FOLDER_NAME,
    DEFAULT_SELECTION_FILE_NAME,
    DEFAULT_TEMPLATES_FOLDER_NAME,
)
from pwnv.models.challenge import Category
from pwnv.plugins import ChallengePlugin
from pwnv.utils.config import get_config_path

_PWNV_CONFIG_BASE_DIR = get_config_path().parent
_PLUGINS_ROOT = _PWNV_CONFIG_BASE_DIR / DEFAULT_PLUGINS_FOLDER_NAME
_TEMPLATES_ROOT = _PWNV_CONFIG_BASE_DIR / DEFAULT_TEMPLATES_FOLDER_NAME


def get_plugins_directory() -> Path:
    _PLUGINS_ROOT.mkdir(parents=True, exist_ok=True)
    return _PLUGINS_ROOT


def get_templates_directory() -> Path:
    _TEMPLATES_ROOT.mkdir(parents=True, exist_ok=True)
    return _TEMPLATES_ROOT


def get_bundled_examples_directory() -> Path:
    return Path(__file__).resolve().parent.parent / DEFAULT_EXAMPLES_FOLDER_NAME


def install_bundled_examples() -> List[Path]:
    import shutil

    source = get_bundled_examples_directory()
    if not source.is_dir():
        return []

    installed: List[Path] = []
    roots = {
        DEFAULT_PLUGINS_FOLDER_NAME: get_plugins_directory(),
        DEFAULT_TEMPLATES_FOLDER_NAME: get_templates_directory(),
    }
    for folder, destination_root in roots.items():
        root = source / folder
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_dir() or path.name == DEFAULT_SELECTION_FILE_NAME:
                continue
            destination = destination_root / path.relative_to(root)
            if destination.exists():
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            installed.append(destination)

    _apply_bundled_selection(source)
    return installed


def _apply_bundled_selection(source: Path) -> None:
    import json

    bundled = source / DEFAULT_PLUGINS_FOLDER_NAME / DEFAULT_SELECTION_FILE_NAME
    if not bundled.is_file():
        return

    try:
        defaults = json.loads(bundled.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    if not isinstance(defaults, dict):
        return

    plugins_directory = get_plugins_directory()
    selection = get_plugin_selection()
    additions = {
        category: name
        for category, name in defaults.items()
        if category not in selection and (plugins_directory / f"{name}.py").is_file()
    }
    if additions:
        save_plugin_selection({**selection, **additions})


def load_template_content(category_name: str, filename: str) -> str:
    template_path = get_templates_directory() / category_name / filename
    if not template_path.is_file():
        raise FileNotFoundError(
            f"Template file '{template_path}' does not exist. "
            f"Please create it in {get_templates_directory()}/{category_name}/"
        )
    return template_path.read_text(encoding="utf-8")


def get_plugin_selection() -> Dict[str, str]:
    import json

    from pwnv.utils.ui import error

    selection_file = get_plugins_directory() / DEFAULT_SELECTION_FILE_NAME
    if not selection_file.is_file():
        return {}

    try:
        with open(selection_file, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        error(
            f"Invalid JSON in selection file: {selection_file}."
            "Returning empty selection."
        )
        return {}


def save_plugin_selection(selection_data: Dict[str, str]) -> None:
    import json

    selection_file = get_plugins_directory() / DEFAULT_SELECTION_FILE_NAME
    selection_file.parent.mkdir(parents=True, exist_ok=True)
    with open(selection_file, "w", encoding="utf-8") as f:
        json.dump(selection_data, f, indent=4, ensure_ascii=False)


def set_selected_plugin_for_category(category: Category, plugin_name: str) -> None:
    selection = get_plugin_selection()
    selection[category.name] = plugin_name
    save_plugin_selection(selection)


def get_selected_plugin_for_category(category: Category) -> ChallengePlugin | None:
    from pwnv.core.plugin_manager import plugin_manager

    selection = get_plugin_selection()
    plugin_name = selection.get(category.name)
    return plugin_manager.get_plugin_by_name(plugin_name)


def remove_selected_plugin_for_category(category: Category) -> None:
    from pwnv.utils.ui import error

    selection = get_plugin_selection()
    if category.name in selection:
        del selection[category.name]
        save_plugin_selection(selection)
    else:
        error(f"No plugin selected for category '{category.name}'.")


def create_plugin_file(
    plugin_file: Path, name: str, category: Category, template_name: str
) -> None:
    plugin_class_name = name.capitalize()
    plugin_code_template = """from pwnv.core import register_plugin
from pwnv.models.challenge import Category
from pwnv.plugins.plugin import ChallengePlugin

@register_plugin
class {plugin_class_name}Plugin(ChallengePlugin):
    templates_to_copy = {{
        "{template_filename}": None,
    }}

    def category(self) -> Category:
        return Category.{category_name}

    def logic(self, challenge):
        ...

"""
    plugin_code = plugin_code_template.format(
        plugin_class_name=plugin_class_name,
        category_name=category.name,
        template_filename=template_name,
    )
    plugin_file.write_text(plugin_code, encoding="utf-8")
