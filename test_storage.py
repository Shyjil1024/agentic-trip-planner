import pytest

from trip_planner import (
    InMemoryTripSessionStore,
    InterviewSessionService,
    TripSession,
)


def make_session():
    return TripSession(trip_id="trip-1", user_id="user-1", destination="Ladakh")


def test_answers_are_saved_and_can_be_resumed():
    service = InterviewSessionService(InMemoryTripSessionStore())
    service.start(make_session())

    result = service.answer("trip-1", {"origin": "Delhi"})
    resumed = service.get("trip-1")

    assert result.session.origin.name == "Delhi"
    assert resumed is not None
    assert resumed.origin.name == "Delhi"
    assert result.next_question.field == "dates"


def test_store_returns_copies_not_mutable_internal_state():
    store = InMemoryTripSessionStore()
    store.create(make_session())
    loaded = store.get("trip-1")
    loaded.destination = "Changed locally"

    assert store.get("trip-1").destination == "Ladakh"


def test_answer_requires_an_existing_trip():
    service = InterviewSessionService(InMemoryTripSessionStore())

    with pytest.raises(KeyError):
        service.answer("missing-trip", {"origin": "Delhi"})
