# Agentic Trip Planner

A stateful travel decision and orchestration platform based on the supplied blueprint.

## Step 1: domain foundation

The first implementation step defines the shared `TripSession` state and its core value objects:

- `Location`
- `DateRange`
- `TravelerCount`
- `Budget`
- `TripStatus`

Validation is deterministic and performed by Pydantic. Agent orchestration, provider tools, persistence, and the API are added in later steps.

## Validate Step 1 locally

Run these commands from the project root (`D:\Trip planner`) in PowerShell:

```powershell
python -m pip install -e ".[dev]"
python -m compileall trip_planner tests
python -m pytest -q
```

Expected test output:

```text
5 passed
```

## Step 2: requirement interview

Step 2 adds `RequirementInterview`, which progressively collects the minimum
requirements needed before research begins. It accepts structured updates,
validates them through the domain models, derives trip duration from supplied
dates, and asks one question at a time in this order:

1. Starting location
2. Travel dates
3. Duration, when dates are not available
4. Budget
5. Traveler count

The traveler count must be explicitly supplied; the domain default of one adult
is not treated as user confirmation.

Run the complete test suite with:

```powershell
python -m pytest -q
```

Interview answers are dynamic at runtime. The `InterviewSessionService` loads
the session by `trip_id`, applies the supplied answer data, validates it, and
saves the updated session through a `TripSessionStore`. Step 2 currently uses
`InMemoryTripSessionStore` for development; it can later be replaced with a
PostgreSQL or Redis-backed implementation without changing the interview rules.

Example Python flow:

```python
from trip_planner import (
	InMemoryTripSessionStore,
	InterviewSessionService,
	TripSession,
)

service = InterviewSessionService(InMemoryTripSessionStore())
service.start(
	TripSession(trip_id="trip-1", user_id="user-1", destination="Ladakh")
)
result = service.answer("trip-1", {"origin": "Delhi"})
print(result.next_question.prompt)
```

The test fixtures use fixed values only to verify behavior. They are not the
runtime source of interview data.

To run a complete dynamic example from PowerShell, use a Python file rather
than entering Python statements directly into PowerShell:

```powershell
python examples\dynamic_interview_storage.py
```

The example stores answers for `trip-demo`, resumes the same session for each
answer, and prints the saved values. The in-memory store lasts only while that
Python process is running. Persistent database storage is a later step.

To test the storage behavior:

```powershell
python -m pytest tests\test_storage.py -q
```

Expected output:

```text
3 passed
```

## Step 3: deterministic budget and constraints

Step 3 adds `BudgetService`. It performs category arithmetic with `Decimal`
and checks hard constraints without using an LLM. Supported checks include
maximum budget, currency, duration, transfer count, and traveler count.

Example Python flow:

```python
from trip_planner import BudgetService, TripSession

session = TripSession(
	trip_id="trip-1",
	user_id="user-1",
	destination="Ladakh",
	duration_days=7,
	constraints={
		"hard": {
			"budget_max": {"amount": 80000, "currency": "INR"},
			"max_transfers": 1,
		}
	},
)
service = BudgetService()
breakdown = service.calculate(
	{"transport": "45000.10", "lodging": 30000, "food": "4999.90"},
	"INR",
)
check = service.validate(session, breakdown, transfers=1)
print(breakdown.total)  # 80000.00
print(check.valid)      # True
```

Run Step 3 tests with:

```powershell
python -m pytest tests\test_budget.py -q
```

## Step 4: specialist contracts

Step 4 defines typed contracts for transport, accommodation, activities,
weather, risk, and provider-tool results. Every result includes a status,
confidence score, source references, assumptions, and warnings. A `partial`
result remains visibly partial and cannot be silently treated as complete.

Run Step 4 tests with:

```powershell
python -m pytest tests\test_contracts.py -q
```

## Step 5: orchestration

Step 5 adds `TripOrchestrator`, an explicit state machine that persists the
interview session, accepts dynamic answers, and starts specialist research only
after the minimum requirements are complete. Specialist handlers are injected
through a mapping, so real provider agents can replace test handlers later.

Run Step 5 tests with:

```powershell
python -m pytest tests\test_orchestration.py -q
```

Run the complete suite with:

```powershell
python -m pytest -q
```

## Step 6: API and persistent storage

Step 6 adds a FastAPI application and `SQLiteTripSessionStore`. The API exposes
`/health`, creates trips with `POST /trips`, accepts dynamic interview answers
with `POST /trips/{trip_id}/messages`, and retrieves saved sessions with
`GET /trips/{trip_id}`. SQLite stores the serialized `TripSession`, so answers
survive application restarts.

Run Step 6 tests with:

```powershell
python -m pytest tests\test_sqlite_storage.py tests\test_api.py -q
```

Start the development server with:

```powershell
python -m uvicorn trip_planner.api.app:app --reload
```

Then open `http://127.0.0.1:8000/docs` for the interactive API documentation.

## Step 7: itinerary validation and targeted replanning

Step 7 adds typed itinerary blocks and an independent `ItineraryValidator`.
It checks date bounds, invalid time ranges, overlapping activities, currency,
and hard budget limits. `TargetedReplanner` removes only the blocks identified
by a validation issue; it does not mutate the original itinerary or regenerate
unaffected days.

Run Step 7 tests with:

```powershell
python -m pytest tests\test_validation.py -q
```

Run the complete suite with:

```powershell
python -m pytest -q
```

## Step 8: live events and what-if simulation

Step 8 adds typed live-trip events such as `FLIGHT_DELAYED`,
`WEATHER_CHANGED`, and `ACTIVITY_CANCELLED`. `LiveTripService` performs
impact analysis from event payload block IDs, repairs only those blocks, and
ignores duplicate event IDs. `WhatIfService` applies hypothetical session
changes without mutating the stored or original session.

Run Step 8 tests with:

```powershell
python -m pytest tests\test_live.py -q
```

Run the complete suite with:

```powershell
python -m pytest -q
```


## Step 9: evaluation and observability

Step 9 adds `EvaluationHarness` for deterministic scenario metrics and
`TraceCollector` for structured operation records. The harness reports
constraint satisfaction, budget accuracy, recovery, pass/fail, and latency
metrics without inventing provider data. Trace spans record success or failure,
duration, metadata, and errors.

Run Step 9 tests with:

```powershell
python -m pytest tests\test_evaluation.py tests\test_observability.py -q
```

Run the complete suite with:

```powershell
python -m pytest -q
```



## Step 10: deployment and end-to-end validation

Step 10 adds a container definition, Docker ignore rules, and an end-to-end
workflow covering interview completion, orchestration readiness, itinerary
creation, and live flight-delay replanning.

Run the end-to-end example with:

```powershell
python examples\end_to_end_workflow.py
```

Expected output includes:

```text
phase=ready
event_replanned=True
remaining_blocks=0
```

Run the integration test and complete suite with:

```powershell
python -m pytest tests\test_end_to_end.py -q
python -m pytest -q
```

Build and run the container:

```powershell
docker build -t agentic-trip-planner .
New-Item -ItemType Directory -Force data
docker run -d --rm --name agentic-trip-planner -p 8000:8000 -v "${PWD}\data:/app" agentic-trip-planner
```

The `/app` volume keeps `trip_planner.sqlite3` across container restarts.
Verify the running API with:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected response:

```text
status
ok
```

## Step 11: provider adapters and fallback

Step 11 adds `ProviderRouter` and `TransportProvider`. Providers return the
shared typed `ToolResult` contract, and the router tries providers in order,
preserving warnings from failed providers. `StaticTransportProvider` provides
deterministic development data; real flight, rail, hotel, weather, and places
adapters can be added without changing orchestration code.

Run Step 11 tests with:

```powershell
python -m pytest tests\test_providers.py -q
```

The provider tests cover exception fallback, failed-result fallback, complete
provider failure, and typed static transport data.

## Traveler-facing chat interface

The API also includes a conversational interface for non-technical users. It
does not require JSON, Python, or field names. Open:

```text
http://127.0.0.1:8000/chat
```

The chat agent starts from a normal message such as:

```text
I want to go to Ladakh
```

It asks one question at a time, understands common plain-language answers,
and stores the extracted requirements in the existing trip session. The
conversation endpoints are `POST /chat/start` and
`POST /chat/{trip_id}/messages`; they are used by the browser page, so normal
travelers do not need to interact with those routes directly.

Run the conversation tests with:

```powershell
python -m pytest tests\test_conversation.py -q
```

## Step 12: traveler UI hardening

The chat UI is the primary traveler interface. It shows progress, handles
connection failures, reveals the planning action only after the interview is
complete, and displays the generated option names without exposing developer
JSON or Python syntax.

Validation:

```powershell
python -m pytest tests\test_conversation.py tests\test_planner_api.py -q
```

## Step 13: provider configuration and retries

`ProviderSettings` reads provider URLs, API keys, timeouts, retry counts, and
the database path from environment variables. `RetryingTransportProvider`
retries transient provider failures before `ProviderRouter` moves to its
fallback. Secrets are not stored in source code.

Example configuration:

```powershell
$env:TRIP_TRANSPORT_URL = "https://provider.example/search"
$env:TRIP_TRANSPORT_API_KEY = "your-key"
$env:TRIP_PROVIDER_TIMEOUT = "5"
$env:TRIP_PROVIDER_RETRIES = "2"
```

Validation:

```powershell
python -m pytest tests\test_config.py tests\test_providers.py -q
```

## Step 14: deterministic solver boundary

`DeterministicSolver` scores candidate itineraries for cost, time, and
experience objectives. This keeps arithmetic and ranking outside the LLM and
provides a stable boundary for replacing the implementation with OR-Tools in
a deployment that needs larger constraint spaces.

Validation:

```powershell
python -m pytest tests\test_solver.py -q
```

## Step 15: production persistence hooks

`TRIP_DATABASE_PATH` controls where SQLite stores sessions. `SQLiteEventStore`
persists processed event IDs, so duplicate webhook deliveries remain ignored
after a service restart. The same storage protocols can be implemented by
PostgreSQL or Redis workers without changing the orchestration API.

Example:

```powershell
$env:TRIP_DATABASE_PATH = "data\trip_planner.sqlite3"
```

Validation:

```powershell
python -m pytest tests\test_persistence_config.py -q
```

## Step 16: security and booking approval

`WebhookVerifier` validates HMAC-SHA256 signatures with constant-time
comparison. `BookingApprovalService` prepares booking requests but changes a
request to `approved` only after an explicit boolean approval. No payment or
booking provider call is performed automatically.

Validation:

```powershell
python -m pytest tests\test_security.py tests\test_planner_booking.py -q
```

## Final manual test

Start or rebuild the container:

```powershell
docker build -t agentic-trip-planner .
New-Item -ItemType Directory -Force data
docker rm -f agentic-trip-planner 2>$null
docker run -d --rm --name agentic-trip-planner -p 8000:8000 -v "${PWD}\data:/app" agentic-trip-planner
```

Check the service:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-WebRequest http://127.0.0.1:8000/chat
```

Open `http://127.0.0.1:8000/chat` and enter these normal-language messages:

```text
I want to go to Ladakh
I am starting from Delhi
I want to travel from 2026-10-01 to 2026-10-07
My budget is 80000 INR
2 adults and 0 children
```

The final response should say that research is starting. The saved trip should
contain destination `Ladakh`, origin `Delhi`, duration `7`, and status
`researching`.

Test planning and approval using the trip ID returned by the chat response:

```powershell
$tripId = "PASTE_TRIP_ID_HERE"
$plan = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/trips/$tripId/plan"
$plan.variants.PSObject.Properties.Name

$whatIf = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/trips/$tripId/what-if" -ContentType "application/json" -Body '{"updates":{"destination":"Manali"}}'
$whatIf.destination

$saved = Invoke-RestMethod "http://127.0.0.1:8000/trips/$tripId"
$saved.destination

$booking = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/trips/$tripId/approve-booking" -ContentType "application/json" -Body '{"approved":true}'
$booking.status
```

Expected results:

```text
cost_optimized
time_optimized
experience_optimized
Manali
Ladakh
approved
```

The `Manali` value is only a what-if result; the saved trip remains `Ladakh`.
Booking remains `pending_approval` until the explicit approval request is sent.

Run all automated validation:

```powershell
python -m compileall -q trip_planner tests examples
python -m pytest -q
```

The local production-MVP implementation is complete. Live flight, hotel,
weather, and activity data require provider-specific credentials and endpoint
adapters; configure those behind the Step 13 interfaces without changing the
chat UI, storage protocols, validation, or orchestration contracts.
