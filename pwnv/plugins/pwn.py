from pwnv.models import Challenge
from pwnv.plugins.plugin import ChallengePlugin
from pwnv.templates import pwn_template


class PwnPlugin(ChallengePlugin):
    category = "pwn"

    def create_template(self, challenge: Challenge):
        path = challenge.path
        with open(path / "solve.py", "w") as f:
            f.write(pwn_template)

    def logic(self, challenge: Challenge):
        return super().logic(challenge)
