"""Plain-language conversation adapter for trip requirement collection."""

import re
from datetime import date
from typing import Any

from uuid import uuid4

from .orchestration import OrchestratorState, TripOrchestrator
from .domain import TripSession


class ConversationResult:
    def __init__(self, state: OrchestratorState, message: str) -> None:
        self.state = state
        self.message = message


class ConversationService:
    """Translate ordinary traveler messages into persisted interview updates."""

    def __init__(self, orchestrator: TripOrchestrator) -> None:
        self.orchestrator = orchestrator

    def start(self, user_id: str, message: str) -> ConversationResult:
        destination = self._destination(message)
        if not destination:
            raise ValueError("Please tell me where you would like to travel.")
        trip_id = f"chat-{uuid4()}"
        state = self.orchestrator.start(
            TripSession(trip_id=trip_id, user_id=user_id, destination=destination)
        )
        return ConversationResult(state, self._opening_message(destination, state))

    def answer(self, trip_id: str, message: str) -> ConversationResult:
        session = self.orchestrator.store.get(trip_id)
        if session is None:
            raise KeyError(f"trip session not found: {trip_id}")
        updates = self._parse_answer(session, message)
        if not updates:
            question = self.orchestrator.interview.advance(session).next_question
            prompt = question.prompt if question else "I have everything needed to start planning."
            return ConversationResult(
                self.orchestrator._state_from_interview(self.orchestrator.interview.advance(session)),
                f"I could not identify that detail yet. {prompt}",
            )
        state = self.orchestrator.answer(trip_id, updates)
        return ConversationResult(state, self._next_message(state))

    @staticmethod
    def _destination(message: str) -> str | None:
        match = re.search(r"\b(?:go|travel|visit|trip)\s+to\s+([A-Za-z][A-Za-z .'-]+)", message, re.IGNORECASE)
        return match.group(1).strip(" .,!?'") if match else None

    def _parse_answer(self, session: TripSession, message: str) -> dict[str, Any]:
        field = self.orchestrator.interview.advance(session).next_question
        if field is None:
            return {}
        if field.field == "origin":
            match = re.search(r"\b(?:from|starting from|leaving from)\s+([A-Za-z][A-Za-z .'-]+)", message, re.IGNORECASE)
            return {"origin": match.group(1).strip(" .,!?'") if match else message.strip()}
        if field.field == "dates":
            dates = re.findall(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b", message)
            if len(dates) >= 2:
                start = date(*map(int, dates[0])).isoformat()
                end = date(*map(int, dates[1])).isoformat()
                return {"dates": {"start": start, "end": end}}
            return {}
        if field.field == "duration_days":
            match = re.search(r"\b(\d+)\s*days?\b", message, re.IGNORECASE)
            return {"duration_days": int(match.group(1))} if match else {}
        if field.field == "budget":
            match = re.search(r"(?:₹|inr\s*)?([\d,]+)\s*(?:inr|rupees|₹)?", message, re.IGNORECASE)
            if match:
                return {"budget": {"amount": float(match.group(1).replace(",", "")), "currency": "INR"}}
            return {}
        if field.field == "travelers":
            adults = re.search(r"(\d+)\s*adults?", message, re.IGNORECASE)
            children = re.search(r"(\d+)\s*children?", message, re.IGNORECASE)
            if adults:
                return {"travelers": {"adults": int(adults.group(1)), "children": int(children.group(1)) if children else 0}}
            return {}
        return {}

    @staticmethod
    def _opening_message(destination: str, state: OrchestratorState) -> str:
        return f"Great, let us plan your trip to {destination}. {state.interview.next_question.prompt}"

    @staticmethod
    def _next_message(state: OrchestratorState) -> str:
        if state.interview.ready_for_research:
            return "Thanks, I have the essentials. I am starting the research now."
        return state.interview.next_question.prompt
