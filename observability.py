"""Small structured trace records for agent and tool execution."""

from contextlib import contextmanager
from datetime import datetime, timezone
from time import perf_counter
from typing import Iterator
from uuid import uuid4

from pydantic import BaseModel, Field


class TraceRecord(BaseModel):
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    operation: str
    started_at: datetime
    duration_ms: float
    status: str
    metadata: dict[str, str] = Field(default_factory=dict)
    error: str | None = None


class TraceCollector:
    def __init__(self) -> None:
        self.records: list[TraceRecord] = []

    @contextmanager
    def span(self, operation: str, metadata: dict[str, str] | None = None) -> Iterator[None]:
        started_at = datetime.now(timezone.utc)
        started = perf_counter()
        try:
            yield
        except Exception as error:
            self.records.append(
                TraceRecord(
                    operation=operation,
                    started_at=started_at,
                    duration_ms=(perf_counter() - started) * 1000,
                    status="failed",
                    metadata=metadata or {},
                    error=str(error),
                )
            )
            raise
        else:
            self.records.append(
                TraceRecord(
                    operation=operation,
                    started_at=started_at,
                    duration_ms=(perf_counter() - started) * 1000,
                    status="success",
                    metadata=metadata or {},
                )
            )
