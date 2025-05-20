from pwnv.models import Challenge
from pwnv.models.challenge import Category
from pwnv.plugins import PwnPlugin
from pwnv.plugins.plugin import ChallengePlugin

PLUGIN_REGISTRY: dict[Category, ChallengePlugin] = {
    Category.pwn: PwnPlugin(),
    # add other plugins here
}


class Core:
    def __init__(self, challenge: Challenge):
        plugin = PLUGIN_REGISTRY.get(challenge.category)
        if plugin:
            plugin.create_template(challenge)
            plugin.logic(challenge)
