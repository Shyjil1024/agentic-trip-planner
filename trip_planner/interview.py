"""Deterministic requirement interview logic for a trip session."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .domain import DateRange, Location, TripSession, TravelerCount


class RequirementField(str):
    """Names of requirements needed before trip research can begin."""

    ORIGIN = "origin"
    DATES = "dates"
    DURATION = "duration_days"
    BUDGET = "budget"
    TRAVELERS = "travelers"


class InterviewQuestion(BaseModel):
    field: str
    prompt: str


class InterviewResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    session: TripSession
    missing_requirements: list[str] = Field(default_factory=list)
    next_question: InterviewQuestion | None = None
    ready_for_research: bool = False


class RequirementInterview:
    """Merge structured answers and select one next requirement question."""

    _question_order = (
        RequirementField.ORIGIN,
        RequirementField.DATES,
        RequirementField.DURATION,
        RequirementField.BUDGET,
        RequirementField.TRAVELERS,
    )
    _questions = {
        RequirementField.ORIGIN: "Where will you be starting your trip from?",
        RequirementField.DATES: "What dates would you like to travel, or what date range should I consider?",
        RequirementField.DURATION: "How many days should the trip last?",
        RequirementField.BUDGET: "What is your total trip budget, including currency?",
        RequirementField.TRAVELERS: "How many adults and children are traveling?",
    }

    def advance(self, session: TripSession, updates: dict[str, Any] | None = None) -> InterviewResult:
        updates = updates or {}
        normalized = self._normalize_updates(session, updates)
        updated_session = TripSession.model_validate(
            {**session.model_dump(), **normalized}
        )
        missing = self.missing_requirements(updated_session)
        question = None
        if missing:
            field = missing[0]
            question = InterviewQuestion(field=field, prompt=self._questions[field])
        return InterviewResult(
            session=updated_session,
            missing_requirements=missing,
            next_question=question,
            ready_for_research=not missing,
        )

    def missing_requirements(self, session: TripSession) -> list[str]:
        missing = []
        for field in self._question_order:
            if field == RequirementField.ORIGIN and session.origin is None:
                missing.append(field)
            elif field == RequirementField.DATES and session.dates is None:
                missing.append(field)
            elif field == RequirementField.DURATION and session.dates is None and session.duration_days is None:
                missing.append(field)
            elif field == RequirementField.BUDGET and session.budget is None:
                missing.append(field)
            elif field == RequirementField.TRAVELERS and not session.travelers_confirmed:
                missing.append(field)
        return missing

    @staticmethod
    def _normalize_updates(session: TripSession, updates: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(updates)
        if "origin" in normalized and isinstance(normalized["origin"], str):
            normalized["origin"] = Location(name=normalized["origin"])
        if "dates" in normalized and isinstance(normalized["dates"], dict):
            normalized["dates"] = DateRange.model_validate(normalized["dates"])
        if "travelers" in normalized and isinstance(normalized["travelers"], dict):
            normalized["travelers"] = TravelerCount.model_validate(normalized["travelers"])
        if "travelers" in normalized:
            normalized["travelers_confirmed"] = True
        if "dates" in normalized and "duration_days" not in normalized:
            normalized["duration_days"] = normalized["dates"].duration_days
        return normalized
