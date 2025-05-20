import uuid
from enum import IntEnum
from pathlib import Path

from pydantic import BaseModel


class Category(IntEnum):
    pwn = 1
    web = 2
    rev = 3
    crypto = 4
    steg = 5
    misc = 6
    osint = 7
    forensics = 8
    hardware = 9
    mobile = 10
    game = 11
    blockchain = 12
    other = 13


class Solved(IntEnum):
    unsolved = 0
    solved = 1


class Challenge(BaseModel):
    id: uuid.UUID | int = uuid.uuid4()
    name: str
    flag: str | None = None
    points: int | None = None
    solved: Solved = Solved.unsolved
    category: Category = Category.pwn
    ctf_id: uuid.UUID
    path: Path
    tags: list[str] | None = None
    extras: dict | None = None
