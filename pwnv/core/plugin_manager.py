import importlib.util
import sys
from functools import lru_cache
from pathlib import Path
from typing import List, Type

from pwnv.constants import DEFAULT_PLUGINS_FOLDER_NAME
from pwnv.models.challenge import Category
from pwnv.plugins import ChallengePlugin
from pwnv.utils.config import get_config_path

_PWNV_CONFIG_BASE_DIR = get_config_path().parent
_PLUGINS_ROOT = _PWNV_CONFIG_BASE_DIR / DEFAULT_PLUGINS_FOLDER_NAME
_PLUGIN_REGISTRY: List[Type[ChallengePlugin]] = []

_PLUGIN_MODULE_PREFIX = "pwnv_plugins"


def plugin_name(plugin) -> str:
    """Return the plugin's user-facing name (its file stem)."""
    return plugin.__module__.rpartition(".")[2]


def register_plugin(cls: Type[ChallengePlugin]) -> Type[ChallengePlugin]:
    if cls not in _PLUGIN_REGISTRY:
        _PLUGIN_REGISTRY.append(cls)
    return cls


class PluginManager:
    def __init__(self):
        self._plugins_root = _PLUGINS_ROOT
        self._registry = _PLUGIN_REGISTRY
        self._loaded = False

    def _import_plugin_module(self, module_path: Path) -> None:
        from pwnv.utils.ui import error

        module_name = f"{_PLUGIN_MODULE_PREFIX}.{module_path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = mod
                try:
                    spec.loader.exec_module(mod)
                except Exception:
                    sys.modules.pop(module_name, None)
                    raise
        except Exception as e:
            error(f"Failed to load plugin module {module_path.name}: {e}")

    def discover_and_load_plugins(self) -> None:
        from pwnv.utils.ui import info

        if self._loaded:
            return

        if self._plugins_root.is_dir():
            for py_file in self._plugins_root.glob("*.py"):
                if py_file.name != "__init__.py":
                    self._import_plugin_module(py_file)
        else:
            info(
                f"Plugins directory not found: {self._plugins_root}. "
                "No plugins to load."
            )
        self._loaded = True

    @lru_cache(maxsize=1)
    def get_all_plugins(self) -> List[ChallengePlugin]:
        self.discover_and_load_plugins()
        return [cls() for cls in self._registry]

    def get_plugins_by_category(self, category: Category) -> List[ChallengePlugin]:
        return [pl for pl in self.get_all_plugins() if pl.category() == category]

    def get_plugin_by_name(self, name: str | None) -> ChallengePlugin | None:
        if not name:
            return None
        self.discover_and_load_plugins()
        plugin_name_lower = name.lower()
        for plugin in self.get_all_plugins():
            if plugin_name(plugin).lower() == plugin_name_lower:
                return plugin
        return None


plugin_manager = PluginManager()
