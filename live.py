"""Live-trip event handling and non-destructive what-if simulation."""

from copy import deepcopy
from enum import StrEnum
from typing import Any
import sqlite3
from uuid import uuid4

from pydantic import BaseModel, Field

from .domain import TripSession
from .itinerary import Itinerary
from .validation import ItineraryValidator, TargetedReplanner, ValidationResult


class TripEventType(StrEnum):
    FLIGHT_DELAYED = "FLIGHT_DELAYED"
    WEATHER_CHANGED = "WEATHER_CHANGED"
    HOTEL_UNAVAILABLE = "HOTEL_UNAVAILABLE"
    ACTIVITY_CANCELLED = "ACTIVITY_CANCELLED"
    USER_LATE = "USER_LATE"
    BUDGET_CHANGED = "BUDGET_CHANGED"


class TripEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    trip_id: str = Field(min_length=1)
    event_type: TripEventType
    payload: dict[str, Any] = Field(default_factory=dict)


class EventHandlingResult(BaseModel):
    event: TripEvent
    duplicate: bool = False
    affected_block_ids: list[str] = Field(default_factory=list)
    itinerary: Itinerary | None = None
    validation: ValidationResult | None = None


class InMemoryEventStore:
    """Idempotency store for webhook/event processing."""

    def __init__(self) -> None:
        self._events: set[str] = set()

    def mark_processed(self, event_id: str) -> bool:
        if event_id in self._events:
            return False
        self._events.add(event_id)
        return True


class SQLiteEventStore:
    """Persistent idempotency store for webhook delivery retries."""

    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        with sqlite3.connect(database_path) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS processed_events (event_id TEXT PRIMARY KEY)")

    def mark_processed(self, event_id: str) -> bool:
        try:
            with sqlite3.connect(self.database_path) as connection:
                connection.execute("INSERT INTO processed_events (event_id) VALUES (?)", (event_id,))
            return True
        except sqlite3.IntegrityError:
            return False


class LiveTripService:
    """Analyze an event and repair only its affected itinerary blocks."""

    _payload_keys = {
        TripEventType.FLIGHT_DELAYED: "block_ids",
        TripEventType.WEATHER_CHANGED: "block_ids",
        TripEventType.HOTEL_UNAVAILABLE: "block_ids",
        TripEventType.ACTIVITY_CANCELLED: "block_ids",
        TripEventType.USER_LATE: "block_ids",
        TripEventType.BUDGET_CHANGED: "block_ids",
    }

    def __init__(
        self,
        event_store: InMemoryEventStore | None = None,
        validator: ItineraryValidator | None = None,
        replanner: TargetedReplanner | None = None,
    ) -> None:
        self.event_store = event_store or InMemoryEventStore()
        self.validator = validator or ItineraryValidator()
        self.replanner = replanner or TargetedReplanner()

    def handle(self, session: TripSession, itinerary: Itinerary, event: TripEvent) -> EventHandlingResult:
        if event.trip_id != session.trip_id or event.trip_id != itinerary.trip_id:
            raise ValueError("event, session, and itinerary trip ids must match")
        if not self.event_store.mark_processed(event.event_id):
            return EventHandlingResult(event=event, duplicate=True)

        key = self._payload_keys[event.event_type]
        affected = [str(block_id) for block_id in event.payload.get(key, [])]
        if not affected:
            return EventHandlingResult(event=event, affected_block_ids=[])

        repaired = self.replanner.remove_blocks(
            itinerary,
            self._issue_for_event(event, affected),
        )
        validation = self.validator.validate(session, repaired)
        return EventHandlingResult(
            event=event,
            affected_block_ids=affected,
            itinerary=repaired,
            validation=validation,
        )

    @staticmethod
    def _issue_for_event(event: TripEvent, block_ids: list[str]):
        from .validation import ItineraryIssue

        return ItineraryIssue(
            code=f"LIVE_EVENT_{event.event_type.value}",
            detail="blocks affected by live trip event",
            block_ids=block_ids,
        )


class WhatIfService:
    """Apply hypothetical session changes without mutating persisted state."""

    def simulate(self, session: TripSession, updates: dict[str, Any]) -> TripSession:
        simulated = deepcopy(session.model_dump())
        simulated.update(updates)
        return TripSession.model_validate(simulated)
