from fastapi.testclient import TestClient

from trip_planner import InMemoryTripSessionStore, TripOrchestrator
from trip_planner.api.app import create_app


def make_client():
    return TestClient(create_app(TripOrchestrator(InMemoryTripSessionStore())))


def test_chat_page_is_available():
    response = make_client().get("/chat")

    assert response.status_code == 200
    assert "Your trip, figured out together" in response.text
    assert "Swagger UI" not in response.text


def test_plain_language_chat_stores_interview_data():
    client = make_client()
    started = client.post(
        "/chat/start",
        json={"user_id": "user-1", "message": "I want to go to Ladakh"},
    )
    trip_id = started.json()["trip_id"]

    origin = client.post(
        f"/chat/{trip_id}/messages",
        json={"message": "I am starting from Delhi"},
    )

    assert started.status_code == 200
    assert "starting your trip" in started.json()["message"].lower()
    assert origin.status_code == 200
    assert "dates" in origin.json()["message"].lower()


def test_chat_requires_a_natural_language_destination():
    response = make_client().post(
        "/chat/start",
        json={"user_id": "user-1", "message": "Hello"},
    )

    assert response.status_code == 422
