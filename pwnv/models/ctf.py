from pydantic import BaseModel
from enum import IntEnum
import uuid
from datetime import datetime
from pathlib import Path


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
