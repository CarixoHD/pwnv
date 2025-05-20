import json
import uuid
from datetime import datetime
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


class Status(IntEnum):
    running = 1
    stopped = 0


class CTF(BaseModel):
    id: uuid.UUID = uuid.uuid4()
    name: str
    created_at: datetime = datetime.now()
    path: Path
    running: Status = Status.running
    url: str | None = None
    username: str | None = None
    password: str | None = None
    token: str | None = None


class Init(BaseModel):
    ctfs_path: Path
    challenge_tags: list[str]
    ctfs: list[CTF] | list[None]
    challenges: list[Challenge] | list[None]


def migrate_config(old_config_path: Path, new_config_path: Path):
    with old_config_path.open() as f:
        data = json.load(f)

    if data.get("default_ctf_path", False):
        ctfs_path = Path.home() / "CTF"
    else:
        ctfs_path = Path(data.get("env_path", "."))

    challenge_tags = data.get("challenge_tags", [])

    ctfs = []
    for c in data.get("ctfs", []):
        ctfs.append(
            CTF(
                id=uuid.UUID(c["id"]),
                name=c["name"],
                created_at=datetime.fromisoformat(c["created_at"]),
                path=Path(c["path"]),
                running=Status(c["running"]),
                url=c.get("url"),
                username=c.get("username"),
                password=c.get("password"),
                token=c.get("token"),
            )
        )

    challenges = []
    for ch in data.get("challenges", []):
        challenges.append(
            Challenge(
                id=uuid.UUID(ch["id"]),
                name=ch["name"],
                flag=ch.get("flag"),
                points=ch.get("points"),
                solved=Solved(ch.get("solved", Solved.unsolved)),
                category=Category(ch.get("category", Category.other)),
                ctf_id=uuid.UUID(ch["ctf_id"]),
                path=Path(ch["path"]),
                tags=ch.get("tags"),
                extras=ch.get("extras"),
            )
        )

    init_model = Init(
        ctfs_path=ctfs_path,
        challenge_tags=challenge_tags,
        ctfs=ctfs,
        challenges=challenges,
    )

    with new_config_path.open("w", encoding="utf-8") as f:
        f.write(init_model.model_dump_json(indent=4))


if __name__ == "__main__":
    migrate_config(Path("config.json"), Path("new_config.json"))
    print("Migration complete. New config written to new_config.json")
