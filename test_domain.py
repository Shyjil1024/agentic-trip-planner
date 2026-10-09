from datetime import date

import pytest
from pydantic import ValidationError

from trip_planner import DateRange, TripSession, TripStatus, TravelerCount


def test_trip_session_defaults_to_interviewing():
    session = TripSession(trip_id="trip-1", user_id="user-1", destination="Ladakh")

    assert session.status is TripStatus.INTERVIEWING
    assert session.travelers.total == 1
    assert session.dates is None


def test_date_range_includes_both_travel_days():
    dates = DateRange(start=date(2026, 10, 1), end=date(2026, 10, 7))

    assert dates.duration_days == 7


def test_date_range_rejects_reversed_dates():
    with pytest.raises(ValidationError):
        DateRange(start=date(2026, 10, 7), end=date(2026, 10, 1))


def test_trip_session_rejects_mismatched_duration():
    with pytest.raises(ValidationError):
        TripSession(
            trip_id="trip-1",
            user_id="user-1",
            destination="Ladakh",
            dates={"start": "2026-10-01", "end": "2026-10-07"},
            duration_days=5,
        )


def test_traveler_count_requires_an_adult():
    with pytest.raises(ValidationError):
        TravelerCount(adults=0)
