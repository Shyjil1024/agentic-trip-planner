"""Run a dynamic interview session against the in-memory store."""

from trip_planner import (
    InMemoryTripSessionStore,
    InterviewSessionService,
    TripSession,
)


service = InterviewSessionService(InMemoryTripSessionStore())
service.start(
    TripSession(
        trip_id="trip-demo",
        user_id="user-demo",
        destination="Ladakh",
    )
)

answers = [
    {"origin": "Delhi"},
    {"dates": {"start": "2026-10-01", "end": "2026-10-07"}},
    {"budget": {"amount": 80000, "currency": "INR"}},
    {"travelers": {"adults": 2, "children": 0}},
]

for answer in answers:
    result = service.answer("trip-demo", answer)
    next_field = result.next_question.field if result.next_question else "complete"
    print(f"saved answer={answer}; next={next_field}")

saved = service.get("trip-demo")
print(f"stored destination={saved.destination}")
print(f"stored origin={saved.origin.name}")
print(f"stored duration_days={saved.duration_days}")
print(f"ready_for_research={result.ready_for_research}")
