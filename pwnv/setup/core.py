from pwnv.models import Challenge
from pwnv.templates import pwn_template

class Core(object):
    def __init__(self, challenge: Challenge):
        self.challenge = challenge
        
        if challenge.category.name == "pwn":
            self.pwn()
        elif challenge.category.name == "web":
            self.web()
        
    
    def pwn(self):
        path = self.challenge.path
        with open(path / "solve.py", "w") as f:
            f.write(pwn_template)
            
    def web(self):
        return "web"