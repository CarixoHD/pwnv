from pwnv.models import Challenge


class Core:
    def __init__(self, challenge: Challenge):
        from pwnv.utils.plugin import get_selected_plugin_for_category
        from pwnv.utils.ui import warn

        plugin = get_selected_plugin_for_category(challenge.category)

        if plugin:
            plugin.create_template(challenge)
            plugin.logic(challenge)
        else:
            warn(
                f"No suitable or selected plugin found for category "
                f"'{challenge.category.name}'. "
                f"Only created directories. Use 'pwnv plugin select' to choose one."
            )
