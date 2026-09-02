from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from pwnv.models import Challenge
from pwnv.models.challenge import Category


@dataclass
class TemplateWriteReport:
    written: List[Path] = field(default_factory=list)
    skipped: List[Path] = field(default_factory=list)


@dataclass(frozen=True)
class _WritePolicy:
    force: bool = False
    suffix: str = ""
    report: TemplateWriteReport | None = None


_policy = _WritePolicy()


@contextmanager
def template_write_policy(
    *, force: bool = False, suffix: str = ""
) -> Generator[TemplateWriteReport]:
    global _policy

    previous = _policy
    report = TemplateWriteReport()
    _policy = _WritePolicy(force=force, suffix=suffix, report=report)
    try:
        yield report
    finally:
        _policy = previous


def _apply_suffix(filename: str, suffix: str) -> str:
    if not suffix:
        return filename
    stem, dot, extension = filename.rpartition(".")
    return f"{stem}{suffix}{dot}{extension}" if dot else f"{filename}{suffix}"


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
        from pwnv.utils.template import render_template
        from pwnv.utils.ui import info

        try:
            text = self._load_template(template_filename)
        except FileNotFoundError:
            info(
                f"Template file '{template_filename}' not found for category "
                f"'{self.category().name}'. Skipping."
            )
            return

        dest_path = challenge.path / _apply_suffix(destination_filename, _policy.suffix)
        if dest_path.exists() and not _policy.force:
            if _policy.report is not None:
                _policy.report.skipped.append(dest_path)
            return

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(render_template(text, challenge), encoding="utf-8")
        if _policy.report is not None:
            _policy.report.written.append(dest_path)
