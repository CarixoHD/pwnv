from pwnv.models.challenge import Challenge
from pwnv.models.ctf import CTF
from pydantic import BaseModel
from pathlib import Path


class Init(BaseModel):
    env_path: Path
    challenge_tags: list[str]
    ctfs: list[CTF] | list[None]
    challenges: list[Challenge] | list[None]
