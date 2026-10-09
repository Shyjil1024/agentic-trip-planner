"""Persistence boundary for trip sessions."""

from copy import deepcopy
from typing import Protocol

from .domain import TripSession
from .interview import InterviewResult, RequirementInterview


class TripSessionStore(Protocol):
    """Storage contract used by the interview workflow."""

    def create(self, session: TripSession) -> TripSession:
        """Persist a new session and return it."""

    def get(self, trip_id: str) -> TripSession | None:
        """Return a session by id, or None when it does not exist."""

    def save(self, session: TripSession) -> TripSession:
        """Persist an updated session and return it."""


class InMemoryTripSessionStore:
    """Temporary process-local store for development and tests."""

    def __init__(self) -> None:
        self._sessions: dict[str, TripSession] = {}

    def create(self, session: TripSession) -> TripSession:
        if session.trip_id in self._sessions:
            raise ValueError(f"trip session already exists: {session.trip_id}")
        return self.save(session)

    def get(self, trip_id: str) -> TripSession | None:
        session = self._sessions.get(trip_id)
        return deepcopy(session) if session else None

    def save(self, session: TripSession) -> TripSession:
        self._sessions[session.trip_id] = deepcopy(session)
        return deepcopy(session)


class InterviewSessionService:
    """Apply dynamic interview answers to sessions held by a store."""

    def __init__(self, store: TripSessionStore, interview: RequirementInterview | None = None) -> None:
        self.store = store
        self.interview = interview or RequirementInterview()

    def start(self, session: TripSession) -> InterviewResult:
        saved = self.store.create(session)
        return self.interview.advance(saved)

    def answer(self, trip_id: str, updates: dict) -> InterviewResult:
        session = self.store.get(trip_id)
        if session is None:
            raise KeyError(f"trip session not found: {trip_id}")
        result = self.interview.advance(session, updates)
        self.store.save(result.session)
        return result

    def get(self, trip_id: str) -> TripSession | None:
        return self.store.get(trip_id)
