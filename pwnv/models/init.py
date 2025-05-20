from pathlib import Path

from pydantic import BaseModel

from pwnv.models.challenge import Challenge
from pwnv.models.ctf import CTF


class Init(BaseModel):
    ctfs_path: Path
    challenge_tags: list[str]
    ctfs: list[CTF] | list[None]
    challenges: list[Challenge] | list[None]
