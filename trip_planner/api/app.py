"""FastAPI application for trip sessions and interview answers."""

from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..domain import TripSession
from ..conversation import ConversationService
from ..orchestration import OrchestratorState, TripOrchestrator
from ..sqlite_storage import SQLiteTripSessionStore
from ..booking import BookingApprovalService, BookingRequest
from ..planner import ItineraryPlanner, PlannedItineraries
from ..live import WhatIfService
from ..config import ProviderSettings


class CreateTripRequest(BaseModel):
    user_id: str = Field(min_length=1)
    destination: str = Field(min_length=1)


class AnswerRequest(BaseModel):
    updates: dict[str, Any] = Field(default_factory=dict)


class ChatStartRequest(BaseModel):
    user_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    trip_id: str
    message: str
    phase: str
    ready_for_research: bool


class WhatIfRequest(BaseModel):
    updates: dict[str, Any] = Field(default_factory=dict)


class ApprovalRequest(BaseModel):
    approved: bool


def create_app(orchestrator: TripOrchestrator | None = None) -> FastAPI:
    if orchestrator is None:
        store = SQLiteTripSessionStore(ProviderSettings.from_environment().database_path)
        orchestrator = TripOrchestrator(store)

    app = FastAPI(title="Agentic Trip Planner", version="0.1.0")
    conversation = ConversationService(orchestrator)
    planner = ItineraryPlanner()
    what_if = WhatIfService()
    booking = BookingApprovalService()
    plans: dict[str, PlannedItineraries] = {}
    bookings: dict[str, BookingRequest] = {}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/chat", response_class=HTMLResponse)
    def chat_page() -> str:
        return CHAT_HTML

    @app.post("/chat/start", response_model=ChatResponse)
    def start_chat(request: ChatStartRequest) -> ChatResponse:
        try:
            result = conversation.start(request.user_id, request.message)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return ChatResponse(
            trip_id=result.state.session.trip_id,
            message=result.message,
            phase=result.state.phase,
            ready_for_research=result.state.interview.ready_for_research,
        )

    @app.post("/chat/{trip_id}/messages", response_model=ChatResponse)
    def chat_message(trip_id: str, request: ChatMessageRequest) -> ChatResponse:
        try:
            result = conversation.answer(trip_id, request.message)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return ChatResponse(
            trip_id=trip_id,
            message=result.message,
            phase=result.state.phase,
            ready_for_research=result.state.interview.ready_for_research,
        )

    @app.post("/trips", response_model=OrchestratorState)
    def create_trip(request: CreateTripRequest) -> OrchestratorState:
        session = TripSession(
            trip_id=str(uuid4()),
            user_id=request.user_id,
            destination=request.destination,
        )
        try:
            return orchestrator.start(session)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/trips/{trip_id}/messages", response_model=OrchestratorState)
    def answer_trip(trip_id: str, request: AnswerRequest) -> OrchestratorState:
        try:
            return orchestrator.answer(trip_id, request.updates)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.get("/trips/{trip_id}", response_model=TripSession)
    def get_trip(trip_id: str) -> TripSession:
        session = orchestrator.store.get(trip_id)
        if session is None:
            raise HTTPException(status_code=404, detail="trip session not found")
        return session

    @app.post("/trips/{trip_id}/plan", response_model=PlannedItineraries)
    def plan_trip(trip_id: str) -> PlannedItineraries:
        session = orchestrator.store.get(trip_id)
        if session is None:
            raise HTTPException(status_code=404, detail="trip session not found")
        try:
            result = planner.plan(session)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        plans[trip_id] = result
        return result

    @app.post("/trips/{trip_id}/what-if", response_model=TripSession)
    def simulate_trip(trip_id: str, request: WhatIfRequest) -> TripSession:
        session = orchestrator.store.get(trip_id)
        if session is None:
            raise HTTPException(status_code=404, detail="trip session not found")
        return what_if.simulate(session, request.updates)

    @app.post("/trips/{trip_id}/approve-booking", response_model=BookingRequest)
    def approve_booking(trip_id: str, request: ApprovalRequest) -> BookingRequest:
        plan = plans.get(trip_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="plan not found")
        itinerary = plan.variants[next(iter(plan.variants))]
        booking_request = booking.prepare(itinerary)
        approved = booking.approve(booking_request, request.approved)
        bookings[approved.booking_id] = approved
        return approved

    return app


app = create_app()


CHAT_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Trip Planner Chat</title>
    <style>
        body { margin: 0; background: #f4f0e8; color: #243238; font: 16px Georgia, serif; }
        main { max-width: 720px; margin: 0 auto; padding: 32px 20px; }
        h1 { margin-bottom: 6px; }
        #messages { min-height: 420px; padding: 18px; background: #fffdf8; border: 1px solid #d8cec0; border-radius: 8px; }
        .message { margin: 12px 0; padding: 12px 14px; border-radius: 8px; white-space: pre-wrap; }
        .agent { background: #e4efe8; }
        .user { background: #f1dfc8; text-align: right; }
        form { display: flex; gap: 10px; margin-top: 14px; }
        input { flex: 1; padding: 13px; border: 1px solid #b9aa99; border-radius: 6px; font: inherit; }
        button { padding: 13px 18px; border: 0; border-radius: 6px; background: #285943; color: white; font: inherit; cursor: pointer; }
    </style>
</head>
<body>
    <main>
        <h1>Your trip, figured out together</h1>
        <p>Tell me where you want to go. I will ask for only what I need.</p>
        <section id="messages" aria-live="polite"></section>
        <p id="status" role="status"></p>
        <button id="plan-button" type="button" hidden>Show my options</button>
        <form id="chat-form">
            <input id="message" autocomplete="off" placeholder="I want to go to Ladakh" required>
            <button type="submit">Send</button>
        </form>
    </main>
    <script>
        let tripId = null;
        const messages = document.getElementById('messages');
        const input = document.getElementById('message');
        const status = document.getElementById('status');
        const planButton = document.getElementById('plan-button');
        function addMessage(text, who) {
            const item = document.createElement('div');
            item.className = `message ${who}`;
            item.textContent = text;
            messages.appendChild(item);
            messages.scrollTop = messages.scrollHeight;
        }
        function setStatus(text) { status.textContent = text; }
        document.getElementById('chat-form').addEventListener('submit', async (event) => {
            event.preventDefault();
            const text = input.value.trim();
            if (!text) return;
            addMessage(text, 'user');
            input.value = '';
            const endpoint = tripId ? `/chat/${tripId}/messages` : '/chat/start';
            const body = tripId ? { message: text } : { user_id: `browser-${crypto.randomUUID()}`, message: text };
            setStatus('Thinking...');
            try {
                const response = await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
                const data = await response.json();
                if (!response.ok) { addMessage(data.detail || 'Something went wrong.', 'agent'); return; }
                tripId = data.trip_id;
                addMessage(data.message, 'agent');
                planButton.hidden = !data.ready_for_research;
                setStatus(data.ready_for_research ? 'Ready to research' : 'Interview in progress');
            } catch (error) {
                addMessage('I could not reach the trip service. Please try again.', 'agent');
                setStatus('Connection problem');
            }
        });
        planButton.addEventListener('click', async () => {
            setStatus('Preparing options...');
            const response = await fetch(`/trips/${tripId}/plan`, { method: 'POST' });
            const data = await response.json();
            if (!response.ok) { addMessage(data.detail || 'I could not prepare options.', 'agent'); return; }
            const names = Object.keys(data.variants).map(name => name.replaceAll('_', ' ')).join(', ');
            addMessage(`I prepared these options: ${names}.`, 'agent');
            setStatus('Options ready');
            planButton.hidden = true;
        });
    </script>
</body>
</html>
"""
