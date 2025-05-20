import uuid
from datetime import datetime
from enum import IntEnum
from pathlib import Path

from pydantic import BaseModel


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
