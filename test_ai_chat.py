from fastapi.testclient import TestClient

from trip_planner import InMemoryTripSessionStore, TripOrchestrator
from trip_planner.api.app import create_app


def test_ai_chat_extracts_multiple_requirements_and_shows_plan(monkeypatch):
    def fake_ai(instructions, context):
        if "Extract ONLY" in instructions:
            return {"reply": "I can help with that.", "destination": "Ladakh", "origin": "Delhi",
                    "dates": {"start": "2026-10-01", "end": "2026-10-02"},
                    "budget": {"amount": 80000, "currency": "INR"},
                    "travelers": {"adults": 2, "children": 0}, "activities": ["photography"]}
        return {"intro": "A two-day idea", "days": [
            {"date": "2026-10-01", "title": "Travel", "activities": ["Arrive"], "notes": "Check roads"},
            {"date": "2026-10-02", "title": "Explore", "activities": ["Photography"], "notes": "Flexible"}],
            "budget_notes": "Prices require verification", "cautions": ["Check travel times"]}

    monkeypatch.setattr('trip_planner.api.app.ask_json', fake_ai)
    monkeypatch.setattr('trip_planner.api.app.road_route', lambda *args: {
        "distance_km": 100, "duration_hours": 2, "hotels": []})
    client = TestClient(create_app(TripOrchestrator(InMemoryTripSessionStore())))
    response = client.post('/ai/chat/start', json={'user_id': 'u', 'message': 'Trip details'})
    assert response.status_code == 200
    assert response.json()['ready_for_research'] is True
    assert response.json()['requirements']['activities'] == ['photography']
    trip_id = response.json()['trip_id']
    plan = client.post(f'/ai/trips/{trip_id}/plan')
    assert plan.status_code == 200
    assert len(plan.json()['days']) == 2


def test_ai_missing_key_reports_setup(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    client = TestClient(create_app(TripOrchestrator(InMemoryTripSessionStore())))
    response = client.post('/ai/chat/start', json={'user_id': 'u', 'message': 'Hi'})
    assert response.status_code == 503
    assert 'OPENAI_API_KEY' in response.json()['detail']
