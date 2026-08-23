from datetime import datetime

from pydantic import BaseModel, Field
from typing import Any, Literal


class LogCreate(BaseModel):
    timestamp: datetime
    level: Literal["debug", "info", "warn", "error"]
    service: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)
    attributes: dict[str, Any] = Field(default_factory=dict)

class LogResponse(BaseModel):
    id: int
    timestamp: datetime
    level: str
    service: str
    message: str
    attributes: dict

class LogCreateResponse(BaseModel):
    id: int
    message: str

class LogBatchCreate(BaseModel):
    logs: list[LogCreate]