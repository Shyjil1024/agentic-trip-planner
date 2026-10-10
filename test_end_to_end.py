from datetime import date, datetime

from trip_planner import (
    InMemoryTripSessionStore,
    Itinerary,
    ItineraryBlock,
    ItineraryDay,
    LiveTripService,
    TripEvent,
    TripEventType,
    TripOrchestrator,
    TripSession,
)


def test_complete_local_workflow_from_interview_to_live_replan():
    orchestrator = TripOrchestrator(InMemoryTripSessionStore())
    started = orchestrator.start(
        TripSession(trip_id="trip-1", user_id="user-1", destination="Ladakh")
    )
    planned = orchestrator.answer(
        "trip-1",
        {
            "origin": "Delhi",
            "dates": {"start": "2026-10-01", "end": "2026-10-01"},
            "budget": {"amount": 80000, "currency": "INR"},
            "travelers": {"adults": 2, "children": 0},
        },
    )
    itinerary = Itinerary(
        itinerary_id="itinerary-1",
        trip_id="trip-1",
        currency="INR",
        days=[
            ItineraryDay(
                date=date(2026, 10, 1),
                blocks=[
                    ItineraryBlock(
                        block_id="arrival",
                        title="Arrival",
                        date=date(2026, 10, 1),
                        start=datetime(2026, 10, 1, 8),
                        end=datetime(2026, 10, 1, 10),
                        location="Leh",
                        currency="INR",
                    )
                ],
            )
        ],
    )

    handled = LiveTripService().handle(
        planned.session,
        itinerary,
        TripEvent(
            trip_id="trip-1",
            event_type=TripEventType.FLIGHT_DELAYED,
            payload={"block_ids": ["arrival"]},
        ),
    )

    assert started.interview.next_question.field == "origin"
    assert planned.interview.ready_for_research is True
    assert handled.validation.valid is True
    assert handled.itinerary.all_blocks() == []
