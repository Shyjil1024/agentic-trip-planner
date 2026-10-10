"""Exercise the complete local trip-planning workflow."""

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

store = InMemoryTripSessionStore()
orchestrator = TripOrchestrator(store)
state = orchestrator.start(
    TripSession(trip_id="demo-trip", user_id="demo-user", destination="Ladakh")
)
state = orchestrator.answer(
    "demo-trip",
    {
        "origin": "Delhi",
        "dates": {"start": "2026-10-01", "end": "2026-10-01"},
        "budget": {"amount": 80000, "currency": "INR"},
        "travelers": {"adults": 2, "children": 0},
    },
)

itinerary = Itinerary(
    itinerary_id="demo-itinerary",
    trip_id="demo-trip",
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

event = TripEvent(
    trip_id="demo-trip",
    event_type=TripEventType.FLIGHT_DELAYED,
    payload={"block_ids": ["arrival"]},
)
handled = LiveTripService().handle(state.session, itinerary, event)
print(f"phase={state.phase}")
print(f"event_replanned={handled.itinerary is not None}")
print(f"remaining_blocks={len(handled.itinerary.all_blocks())}")
