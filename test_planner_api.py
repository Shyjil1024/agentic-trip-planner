from fastapi.testclient import TestClient

from trip_planner import InMemoryTripSessionStore, TripOrchestrator
from trip_planner.api.app import create_app


def test_plan_what_if_and_booking_routes():
    client = TestClient(create_app(TripOrchestrator(InMemoryTripSessionStore())))
    created = client.post("/trips", json={"user_id": "user-1", "destination": "Ladakh"})
    trip_id = created.json()["session"]["trip_id"]
    client.post(
        f"/trips/{trip_id}/messages",
        json={"updates": {"origin": "Delhi", "dates": {"start": "2026-10-01", "end": "2026-10-02"}, "budget": {"amount": 80000, "currency": "INR"}, "travelers": {"adults": 2, "children": 0}}},
    )

    plan = client.post(f"/trips/{trip_id}/plan")
    simulated = client.post(f"/trips/{trip_id}/what-if", json={"updates": {"destination": "Manali"}})
    booking = client.post(f"/trips/{trip_id}/approve-booking", json={"approved": True})
    saved = client.get(f"/trips/{trip_id}")

    assert plan.status_code == 200
    assert len(plan.json()["variants"]) == 3
    assert simulated.json()["destination"] == "Manali"
    assert saved.json()["destination"] == "Ladakh"
    assert booking.json()["status"] == "approved"
