from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DatasetName(StrEnum):
    HDFS = "hdfs"
    BGL = "bgl"


class LogEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    dataset: DatasetName
    source: str = Field(min_length=1, max_length=256)
    host_hash: str = Field(min_length=3, max_length=128)
    severity: str = Field(min_length=1, max_length=32)
    message: str = Field(min_length=1, max_length=32_768)
    ground_truth_label: int = Field(ge=0, le=1)
    group_hash: str | None = Field(default=None, max_length=128)

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value


class EventSequence(BaseModel):
    model_config = ConfigDict(frozen=True)

    sequence_id: str
    dataset: DatasetName
    started_at: datetime
    ended_at: datetime
    events: tuple[LogEvent, ...]
    label: int = Field(ge=0, le=1)

