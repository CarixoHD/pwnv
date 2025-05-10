from pwnv.models import Challenge
from pwnv.models.challenge import Category
from pwnv.plugins.plugin import ChallengePlugin
from pwnv.plugins import PwnPlugin


PLUGIN_REGISTRY: dict[Category, ChallengePlugin] = {
    Category.pwn: PwnPlugin(),
    # add other plugins here
}


class Core(object):
    def __init__(self, challenge: Challenge):
        print(PLUGIN_REGISTRY)
        plugin = PLUGIN_REGISTRY.get(challenge.category)
        if not plugin:
            raise ValueError(f"Plugin for category {challenge.category} not found.")
        plugin.create_template(challenge)
        plugin.logic(challenge)
