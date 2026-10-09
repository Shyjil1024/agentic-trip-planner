"""OpenAI backed conversation and grounded itinerary drafting."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AIUnavailable(Exception):
    pass


def ask_json(instructions: str, context: dict) -> dict:
    from groq import Groq, APIStatusError, APIConnectionError

    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        raise AIUnavailable("Set GROQ_API_KEY and restart the server.")

    try:
        client = Groq(api_key=key, timeout=35.0)
        completion = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            messages=[
                {
                    "role": "system",
                    "content": instructions + " Return one valid JSON object only.",
                },
                {
                    "role": "user",
                    "content": json.dumps(context, ensure_ascii=False),
                },
            ],
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content
        output = json.loads(content or "")
        if not isinstance(output, dict):
            raise ValueError("Expected a JSON object")
        return output
    except APIStatusError as error:
        raise AIUnavailable(
            f"Groq SDK returned HTTP {error.status_code}."
        ) from error
    except APIConnectionError as error:
        raise AIUnavailable(
            "Could not connect to Groq. Check your connection."
        ) from error
    except (ValueError, IndexError, AttributeError) as error:
        raise AIUnavailable(
            "Groq returned an invalid trip response. Please try again."
        ) from error

EXTRACT_PROMPT = """You are a trip planning assistant. Extract ONLY details explicitly stated in the latest message.
Return JSON with keys reply (friendly brief response), destination (string or null),
origin (string or null), dates (object with start/end ISO dates or null),
duration_days (integer or null), budget (object with amount numeric and currency 3 letters or null),
travelers (object with adults integer and children integer or null), activities (list of strings).
Current date is provided for relative dates. Do not invent facts. For messages that are merely greetings,
reply naturally and leave details null. Read current trip details for context; output ONLY updates from latest message.
If user changes a previously stored value, include the new value. If a date range is given, duration_days should be null.
Do not treat hotel ratings or prices as known facts."""


PLAN_PROMPT = """Create a useful day-by-day travel suggestion for this trip using only provided details.
Return JSON: {"intro": string, "days": [{"date": ISO date string, "title": string,
"activities": [string], "notes": string}], "budget_notes": string, "cautions": [string]}.
All day dates must be within the provided trip dates. Activities are SUGGESTIONS, not verified opening hours,
prices, bookings, or travel times. Do not invent hotel names, ratings, availability, live prices, or routes.
Mention the route time and hotel data only if present in the supplied context. Be realistic about distance
and the travel days. If only a duration is known and no start date, date can be an empty string.
Do not claim that the total budget is feasible without actual priced transport and accommodation."""
