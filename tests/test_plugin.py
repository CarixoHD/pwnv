import importlib
import shutil
from pathlib import Path

from pwnv.models.challenge import Category


def _reload_modules():
    config = importlib.import_module("pwnv.utils.config")
    plugin = importlib.import_module("pwnv.utils.plugin")
    manager_mod = importlib.import_module("pwnv.core.plugin_manager")
    importlib.reload(config)
    importlib.reload(plugin)
    importlib.reload(manager_mod)
    return plugin, manager_mod


def test_plugin_selection(tmp_path, monkeypatch):
    monkeypatch.setenv('PWNV_CONFIG', str(tmp_path / 'cfg.json'))
    plugin, manager = _reload_modules()

    root = Path(__file__).resolve().parents[1]
    plugin_src = root / 'plugin_examples' / 'plugins' / 'pwn_example.py'
    dest_dir = plugin.get_plugins_directory()
    shutil.copy(plugin_src, dest_dir / plugin_src.name)

    manager.plugin_manager.discover_and_load_plugins()

    plugin.set_selected_plugin_for_category(Category.pwn, 'pwn_example')
    loaded = plugin.get_selected_plugin_for_category(Category.pwn)
    assert loaded is not None
    assert loaded.__class__.__name__ == 'PwnPlugin'

    plugin.remove_selected_plugin_for_category(Category.pwn)
    assert plugin.get_selected_plugin_for_category(Category.pwn) is None
