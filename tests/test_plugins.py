import textwrap

from pwnv.models.challenge import Category
from pwnv.utils.plugin import (
    get_plugin_selection,
    get_plugins_directory,
    get_selected_plugin_for_category,
    save_plugin_selection,
    set_selected_plugin_for_category,
)


def test_plugin_lookup_is_case_insensitive(tmp_path):
    from pwnv.core.plugin_manager import plugin_manager, plugin_name

    plugins_dir = get_plugins_directory()
    plugin_path = plugins_dir / "CustomMixedCase.py"

    plugin_source = textwrap.dedent(
        """
        from pwnv.core import register_plugin
        from pwnv.models.challenge import Category
        from pwnv.plugins.plugin import ChallengePlugin

        @register_plugin
        class CustomMixedCasePlugin(ChallengePlugin):
            def category(self):
                return Category.pwn

            def logic(self, challenge):
                ...
        """
    )
    plugin_path.write_text(plugin_source, encoding="utf-8")

    # Reset plugin manager caches so it loads our new plugin
    plugin_manager._loaded = False  # type: ignore[attr-defined]
    plugin_manager.get_all_plugins.cache_clear()  # type: ignore[attr-defined]

    plugins = plugin_manager.get_all_plugins()
    assert any(plugin_name(p) == "CustomMixedCase" for p in plugins)

    # Case-insensitive direct lookup
    assert plugin_manager.get_plugin_by_name("custommixedcase") is not None
    assert plugin_manager.get_plugin_by_name("CUSTOMMIXEDCASE") is not None

    # Selection respects stored name but lookup remains case-insensitive
    set_selected_plugin_for_category(Category.pwn, "custommixedcase")
    selected = get_selected_plugin_for_category(Category.pwn)
    assert selected is not None
    assert plugin_name(selected) == "CustomMixedCase"

    # Verify the selection file stored exactly what we set
    selection = get_plugin_selection()
    assert selection[Category.pwn.name] == "custommixedcase"

    # Changing selection casing still resolves to the same plugin
    save_plugin_selection({Category.pwn.name: "CUSTOMMIXEDCASE"})
    selected_again = get_selected_plugin_for_category(Category.pwn)
    assert selected_again is not None
    assert plugin_name(selected_again) == "CustomMixedCase"
