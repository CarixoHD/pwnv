from pydantic import BaseModel
from enum import IntEnum
import uuid
from pathlib import Path


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


class Solved(IntEnum):
    unsolved = 0
    solved = 1


class Challenge(BaseModel):
    id: uuid.UUID = uuid.uuid4()
    name: str
    flag: str | None = None
    points: int | None = None
    solved: Solved = Solved.unsolved
    category: Category = Category.pwn
    ctf_id: uuid.UUID
    path: Path
    tags: list[str] | None = None
