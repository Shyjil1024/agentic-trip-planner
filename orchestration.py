"""Explicit orchestration state machine for interview and research."""

from collections.abc import Callable, Mapping
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from .contracts import AgentName, ResultStatus, SpecialistResponse
from .domain import TripSession, TripStatus
from .interview import InterviewResult, RequirementInterview
from .storage import TripSessionStore


class OrchestrationPhase(StrEnum):
    INTERVIEWING = "interviewing"
    RESEARCHING = "researching"
    READY = "ready"
    DEGRADED = "degraded"


SpecialistHandler = Callable[[TripSession], SpecialistResponse]


class OrchestratorState(BaseModel):
    session: TripSession
    phase: OrchestrationPhase
    interview: InterviewResult
    specialist_results: dict[str, SpecialistResponse] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class TripOrchestrator:
    """Coordinate persisted interview state and injected specialist handlers."""

    def __init__(
        self,
        store: TripSessionStore,
        specialists: Mapping[AgentName | str, SpecialistHandler] | None = None,
        interview: RequirementInterview | None = None,
    ) -> None:
        self.store = store
        self.specialists = {str(name): handler for name, handler in (specialists or {}).items()}
        self.interview = interview or RequirementInterview()

    def start(self, session: TripSession) -> OrchestratorState:
        saved = self.store.create(session)
        interview_result = self.interview.advance(saved)
        return self._state_from_interview(interview_result)

    def answer(self, trip_id: str, updates: dict[str, Any]) -> OrchestratorState:
        session = self.store.get(trip_id)
        if session is None:
            raise KeyError(f"trip session not found: {trip_id}")

        interview_result = self.interview.advance(session, updates)
        self.store.save(interview_result.session)
        if not interview_result.ready_for_research:
            return self._state_from_interview(interview_result)
        return self._research(interview_result.session, interview_result)

    def _research(self, session: TripSession, interview_result: InterviewResult) -> OrchestratorState:
        researching_session = session.model_copy(update={"status": TripStatus.RESEARCHING})
        self.store.save(researching_session)
        results: dict[str, SpecialistResponse] = {}
        errors: list[str] = []

        for name, handler in self.specialists.items():
            try:
                response = handler(researching_session)
                results[name] = response
            except Exception as error:
                errors.append(f"{name}: {error}")
                results[name] = SpecialistResponse(
                    agent=AgentName(name),
                    status=ResultStatus.FAILED,
                    confidence=0,
                    warnings=["specialist handler failed"],
                )

        phase = OrchestrationPhase.DEGRADED if errors else OrchestrationPhase.READY
        return OrchestratorState(
            session=researching_session,
            phase=phase,
            interview=interview_result,
            specialist_results=results,
            errors=errors,
        )

    @staticmethod
    def _state_from_interview(result: InterviewResult) -> OrchestratorState:
        return OrchestratorState(
            session=result.session,
            phase=OrchestrationPhase.INTERVIEWING,
            interview=result,
        )
