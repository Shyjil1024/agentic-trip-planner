from datetime import date, datetime

import pytest

from trip_planner import TripSession
from trip_planner.itinerary import Itinerary, ItineraryBlock, ItineraryDay
from trip_planner.live import LiveTripService, TripEvent, TripEventType, WhatIfService


def make_session():
    return TripSession(
        trip_id="trip-1",
        user_id="user-1",
        destination="Ladakh",
        duration_days=1,
    )


def make_itinerary():
    day = date(2026, 10, 1)
    return Itinerary(
        itinerary_id="itinerary-1",
        trip_id="trip-1",
        currency="INR",
        days=[
            ItineraryDay(
                date=day,
                blocks=[
                    ItineraryBlock(
                        block_id="affected",
                        title="Affected block",
                        date=day,
                        start=datetime(2026, 10, 1, 8),
                        end=datetime(2026, 10, 1, 10),
                        location="Leh",
                        currency="INR",
                    ),
                    ItineraryBlock(
                        block_id="untouched",
                        title="Untouched block",
                        date=day,
                        start=datetime(2026, 10, 1, 12),
                        end=datetime(2026, 10, 1, 14),
                        location="Leh",
                        currency="INR",
                    ),
                ],
            )
        ],
    )


def test_live_event_repairs_only_affected_blocks():
    event = TripEvent(
        event_id="event-1",
        trip_id="trip-1",
        event_type=TripEventType.FLIGHT_DELAYED,
        payload={"block_ids": ["affected"]},
    )

    result = LiveTripService().handle(make_session(), make_itinerary(), event)

    assert result.duplicate is False
    assert result.affected_block_ids == ["affected"]
    assert [block.block_id for block in result.itinerary.days[0].blocks] == ["untouched"]


def test_duplicate_events_are_ignored():
    event = TripEvent(
        event_id="event-1",
        trip_id="trip-1",
        event_type=TripEventType.WEATHER_CHANGED,
        payload={"block_ids": ["affected"]},
    )
    service = LiveTripService()

    service.handle(make_session(), make_itinerary(), event)
    duplicate = service.handle(make_session(), make_itinerary(), event)

    assert duplicate.duplicate is True
    assert duplicate.itinerary is None


def test_event_requires_matching_trip_ids():
    event = TripEvent(
        trip_id="other-trip",
        event_type=TripEventType.ACTIVITY_CANCELLED,
        payload={"block_ids": ["affected"]},
    )

    with pytest.raises(ValueError):
        LiveTripService().handle(make_session(), make_itinerary(), event)


def test_what_if_does_not_mutate_original_session():
    session = make_session()

    simulated = WhatIfService().simulate(session, {"destination": "Manali"})

    assert simulated.destination == "Manali"
    assert session.destination == "Ladakh"
