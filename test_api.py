from fastapi.testclient import TestClient

from trip_planner import InMemoryTripSessionStore, TripOrchestrator
from trip_planner.api.app import create_app


def make_client():
    orchestrator = TripOrchestrator(InMemoryTripSessionStore())
    return TestClient(create_app(orchestrator))


def test_health_endpoint():
    response = make_client().get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_resume_trip_over_http():
    client = make_client()
    created = client.post("/trips", json={"user_id": "user-1", "destination": "Ladakh"})
    trip_id = created.json()["session"]["trip_id"]

    answered = client.post(
        f"/trips/{trip_id}/messages",
        json={"updates": {"origin": "Delhi"}},
    )
    fetched = client.get(f"/trips/{trip_id}")

    assert created.status_code == 200
    assert answered.status_code == 200
    assert answered.json()["session"]["origin"]["name"] == "Delhi"
    assert fetched.json()["origin"]["name"] == "Delhi"


def test_missing_trip_returns_not_found():
    response = make_client().post(
        "/trips/missing/messages",
        json={"updates": {"origin": "Delhi"}},
    )

    assert response.status_code == 404


def test_road_route_requires_origin_and_returns_map_data(monkeypatch):
    client = make_client()
    trip_id = client.post('/trips', json={'user_id': 'u', 'destination': 'Ladakh'}).json()['session']['trip_id']
    assert client.get(f'/trips/{trip_id}/road-route').status_code == 422
    client.post(f'/trips/{trip_id}/messages', json={'updates': {'origin': 'Delhi'}})
    monkeypatch.setattr('trip_planner.api.app.road_route', lambda origin, destination: {
        'origin': origin, 'destination': destination, 'distance_km': 100,
    })
    response = client.get(f'/trips/{trip_id}/road-route')
    assert response.status_code == 200
    assert response.json()['origin'] == 'Delhi'
