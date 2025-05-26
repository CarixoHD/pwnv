from abc import ABC, abstractmethod
from typing import Dict

from pwnv.models import Challenge
from pwnv.models.challenge import Category


class ChallengePlugin(ABC):
    templates_to_copy: Dict[str, str | None] = {"solve.py": None}

    @abstractmethod
    def category(self) -> Category:
        raise NotImplementedError("Plugin must implement a `category` method.")

    @abstractmethod
    def logic(self, challenge: Challenge) -> None:
        raise NotImplementedError("Plugin must implement a `logic` method.")

    def create_template(self, challenge: Challenge) -> None:
        for src_file, dest_file in self.templates_to_copy.items():
            dest = dest_file or src_file
            self._write_template(challenge, src_file, dest)

    def _load_template(self, filename: str) -> str:
        from pwnv.utils.plugin import load_template_content

        return load_template_content(self.category().name, filename)

    def _write_template(
        self, challenge: Challenge, template_filename: str, destination_filename: str
    ) -> None:
        from pwnv.utils.ui import info

        try:
            text = self._load_template(template_filename)
            dest_path = challenge.path / destination_filename
            dest_path.write_text(text)
        except FileNotFoundError:
            info(
                f"Template file '{template_filename}' not found for category "
                f"'{self.category().name}'. Skipping."
            )
