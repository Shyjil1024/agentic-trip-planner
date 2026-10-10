from datetime import date, datetime
from decimal import Decimal

from trip_planner import TripSession
from trip_planner.itinerary import Itinerary, ItineraryBlock, ItineraryDay
from trip_planner.validation import ItineraryIssue, ItineraryValidator, TargetedReplanner, ValidationResult


def make_session(constraints=None):
    return TripSession(
        trip_id="trip-1",
        user_id="user-1",
        destination="Ladakh",
        dates={"start": "2026-10-01", "end": "2026-10-02"},
        duration_days=2,
        constraints=constraints or {},
    )


def block(block_id, start_hour, end_hour, day=date(2026, 10, 1), cost="100"):
    return ItineraryBlock(
        block_id=block_id,
        title=block_id,
        date=day,
        start=datetime(day.year, day.month, day.day, start_hour),
        end=datetime(day.year, day.month, day.day, end_hour),
        location="Leh",
        cost=Decimal(cost),
        currency="INR",
    )


def make_itinerary(*blocks, currency="INR"):
    return Itinerary(
        itinerary_id="itinerary-1",
        trip_id="trip-1",
        currency=currency,
        days=[ItineraryDay(date=date(2026, 10, 1), blocks=list(blocks))],
    )


def test_validator_accepts_feasible_itinerary():
    result = ItineraryValidator().validate(make_session(), make_itinerary(block("a", 9, 11)))

    assert result.valid is True
    assert result.issues == []


def test_validator_detects_overlap_and_invalid_time_range():
    itinerary = make_itinerary(block("a", 9, 11), block("b", 10, 12), block("bad", 14, 13))

    result = ItineraryValidator().validate(make_session(), itinerary)
    codes = {issue.code for issue in result.issues}

    assert codes == {"OVERLAPPING_BLOCKS", "INVALID_TIME_RANGE"}


def test_validator_detects_date_and_budget_violations():
    outside = block("outside", 9, 10, day=date(2026, 10, 3), cost="100")
    itinerary = make_itinerary(outside, currency="INR")
    itinerary.days[0].blocks.append(block("expensive", 11, 12, cost="1000"))
    session = make_session({"hard": {"budget_max": {"amount": 500, "currency": "INR"}}})

    result = ItineraryValidator().validate(session, itinerary)
    codes = {issue.code for issue in result.issues}

    assert codes == {"BLOCK_OUTSIDE_TRIP_DATES", "ITINERARY_BUDGET_EXCEEDED"}


def test_replanner_removes_only_affected_blocks():
    itinerary = make_itinerary(block("a", 9, 11), block("b", 12, 13))
    issue = ValidationResult(
        valid=False,
        issues=[ItineraryIssue(code="OVERLAPPING_BLOCKS", detail="bad", block_ids=["a"])],
    )

    repaired = TargetedReplanner().repair_first_issue(itinerary, issue)

    assert [item.block_id for item in repaired.days[0].blocks] == ["b"]
    assert [item.block_id for item in itinerary.days[0].blocks] == ["a", "b"]


def test_replanner_does_not_change_valid_itinerary():
    itinerary = make_itinerary(block("a", 9, 11))
    validation = ItineraryValidator().validate(make_session(), itinerary)

    assert TargetedReplanner().repair_first_issue(itinerary, validation) == itinerary
