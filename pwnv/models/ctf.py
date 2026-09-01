import uuid
from datetime import datetime
from enum import IntEnum
from pathlib import Path

from pydantic import BaseModel, Field


class Status(IntEnum):
    running = 1
    stopped = 0


class CTF(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    created_at: datetime = Field(default_factory=datetime.now)
    path: Path
    running: Status = Status.running
    url: str | None = None
    # The platform ctfbridge should talk to, when its own detection got it
    # wrong. ``None`` means "detect", which is right for almost every event.
    platform: str | None = None
