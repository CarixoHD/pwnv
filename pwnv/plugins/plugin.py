from abc import ABC, abstractmethod

from pwnv.models import Challenge


class ChallengePlugin(ABC):
    category: str

    def __init__(self):
        if not hasattr(self, "category") or not isinstance(self.category, str):
            raise TypeError("Plugin must define a `category` string.")

    @abstractmethod
    def create_template(self, challenge: Challenge) -> None:
        pass

    @abstractmethod
    def logic(self, challenge: Challenge) -> None:
        pass
