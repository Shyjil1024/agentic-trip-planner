from trip_planner import TripSession
from trip_planner.booking import BookingApprovalService, BookingStatus
from trip_planner.planner import ItineraryPlanner, ItineraryVariant


def complete_session():
    return TripSession(
        trip_id="trip-1",
        user_id="user-1",
        destination="Ladakh",
        origin={"name": "Delhi"},
        dates={"start": "2026-10-01", "end": "2026-10-02"},
        duration_days=2,
        budget={"amount": 80000, "currency": "INR"},
        travelers={"adults": 2, "children": 0},
        travelers_confirmed=True,
    )


def test_planner_creates_three_valid_variants():
    result = ItineraryPlanner().plan(complete_session())

    assert set(result.variants) == set(ItineraryVariant)
    assert all(result.validations[variant].valid for variant in ItineraryVariant)


def test_booking_requires_explicit_approval():
    itinerary = ItineraryPlanner().plan(complete_session()).variants[ItineraryVariant.COST_OPTIMIZED]
    service = BookingApprovalService()
    pending = service.prepare(itinerary)

    assert pending.status is BookingStatus.PENDING_APPROVAL
    assert service.approve(pending, False).status is BookingStatus.REJECTED
    assert service.approve(pending, True).status is BookingStatus.APPROVED
