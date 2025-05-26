from pwnv.core import register_plugin
from pwnv.models.challenge import Category
from pwnv.plugins.plugin import ChallengePlugin


@register_plugin
class PwnPlugin(ChallengePlugin):
    templates_to_copy = {
        "rop.py": "solve.py",
    }

    def category(self) -> Category:
        return Category.pwn

    def logic(self, challenge):
        if challenge:
            print("Hello from PwnPlugin!")
