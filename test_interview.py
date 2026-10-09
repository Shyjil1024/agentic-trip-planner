from trip_planner import TripSession
from trip_planner.interview import RequirementInterview


def make_session():
    return TripSession(trip_id="trip-1", user_id="user-1", destination="Ladakh")


def test_interview_asks_for_origin_first():
    result = RequirementInterview().advance(make_session())

    assert result.missing_requirements[0] == "origin"
    assert result.next_question.field == "origin"


def test_interview_derives_duration_from_dates():
    result = RequirementInterview().advance(
        make_session(),
        {
            "origin": "Delhi",
            "dates": {"start": "2026-10-01", "end": "2026-10-07"},
        },
    )

    assert result.session.duration_days == 7
    assert result.next_question.field == "budget"


def test_interview_requires_explicit_traveler_confirmation():
    result = RequirementInterview().advance(
        make_session(),
        {
            "origin": "Delhi",
            "dates": {"start": "2026-10-01", "end": "2026-10-07"},
            "budget": {"amount": 80000, "currency": "INR"},
        },
    )

    assert result.ready_for_research is False
    assert result.next_question.field == "travelers"


def test_interview_is_ready_after_minimum_requirements_are_supplied():
    result = RequirementInterview().advance(
        make_session(),
        {
            "origin": "Delhi",
            "dates": {"start": "2026-10-01", "end": "2026-10-07"},
            "budget": {"amount": 80000, "currency": "INR"},
            "travelers": {"adults": 2, "children": 0},
        },
    )

    assert result.ready_for_research is True
    assert result.missing_requirements == []
    assert result.next_question is None
