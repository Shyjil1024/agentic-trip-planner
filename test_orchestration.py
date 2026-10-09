from trip_planner import InMemoryTripSessionStore, TripSession
from trip_planner.contracts import AgentName, ResultStatus, SpecialistResponse
from trip_planner.orchestration import OrchestrationPhase, TripOrchestrator


def make_session():
    return TripSession(trip_id="trip-1", user_id="user-1", destination="Ladakh")


def complete_answers():
    return {
        "origin": "Delhi",
        "dates": {"start": "2026-10-01", "end": "2026-10-07"},
        "budget": {"amount": 80000, "currency": "INR"},
        "travelers": {"adults": 2, "children": 0},
    }


def test_orchestrator_does_not_research_during_interview():
    calls = []
    orchestrator = TripOrchestrator(
        InMemoryTripSessionStore(),
        {AgentName.TRANSPORT: lambda session: calls.append(session.trip_id)},
    )

    state = orchestrator.start(make_session())

    assert state.phase is OrchestrationPhase.INTERVIEWING
    assert calls == []
    assert state.interview.next_question.field == "origin"


def test_orchestrator_dispatches_specialists_after_requirements_are_ready():
    calls = []

    def transport_handler(session):
        calls.append(session.trip_id)
        return SpecialistResponse(
            agent=AgentName.TRANSPORT,
            status=ResultStatus.SUCCESS,
            confidence=0.9,
        )

    orchestrator = TripOrchestrator(
        InMemoryTripSessionStore(),
        {AgentName.TRANSPORT: transport_handler},
    )
    orchestrator.start(make_session())
    state = orchestrator.answer("trip-1", complete_answers())

    assert state.phase is OrchestrationPhase.READY
    assert state.session.status.value == "researching"
    assert state.specialist_results["transport"].status is ResultStatus.SUCCESS
    assert calls == ["trip-1"]


def test_orchestrator_degrades_when_a_specialist_fails():
    def broken_handler(session):
        raise RuntimeError("provider unavailable")

    orchestrator = TripOrchestrator(
        InMemoryTripSessionStore(),
        {AgentName.WEATHER: broken_handler},
    )
    orchestrator.start(make_session())
    state = orchestrator.answer("trip-1", complete_answers())

    assert state.phase is OrchestrationPhase.DEGRADED
    assert state.errors == ["weather: provider unavailable"]
    assert state.specialist_results["weather"].status is ResultStatus.FAILED
