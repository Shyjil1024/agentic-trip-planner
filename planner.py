"""Deterministic itinerary variant generation for the MVP."""

from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel

from .domain import TripSession
from .itinerary import Itinerary, ItineraryBlock, ItineraryDay
from .validation import ItineraryValidator, ValidationResult


class ItineraryVariant(StrEnum):
    COST_OPTIMIZED = "cost_optimized"
    TIME_OPTIMIZED = "time_optimized"
    EXPERIENCE_OPTIMIZED = "experience_optimized"


class PlannedItineraries(BaseModel):
    trip_id: str
    variants: dict[ItineraryVariant, Itinerary]
    validations: dict[ItineraryVariant, ValidationResult]


class ItineraryPlanner:
    """Create deterministic MVP variants until live candidates are connected."""

    def __init__(self, validator: ItineraryValidator | None = None) -> None:
        self.validator = validator or ItineraryValidator()

    def plan(self, session: TripSession) -> PlannedItineraries:
        if not session.dates or not session.origin:
            raise ValueError("origin and dates are required before planning")
        variants = {
            variant: self._build_variant(session, variant)
            for variant in ItineraryVariant
        }
        return PlannedItineraries(
            trip_id=session.trip_id,
            variants=variants,
            validations={
                variant: self.validator.validate(session, itinerary)
                for variant, itinerary in variants.items()
            },
        )

    def _build_variant(self, session: TripSession, variant: ItineraryVariant) -> Itinerary:
        days = []
        for offset in range(session.dates.duration_days):
            day = session.dates.start + timedelta(days=offset)
            if variant is ItineraryVariant.COST_OPTIMIZED:
                cost, title = Decimal("0"), "Flexible local day"
            elif variant is ItineraryVariant.TIME_OPTIMIZED:
                cost, title = Decimal("1500"), "Central highlights"
            else:
                cost, title = Decimal("3000"), "Photography and culture"
            start = datetime.combine(day, datetime.min.time()).replace(hour=9)
            days.append(
                ItineraryDay(
                    date=day,
                    blocks=[
                        ItineraryBlock(
                            block_id=f"{variant.value}-{offset + 1}",
                            title=title,
                            date=day,
                            start=start,
                            end=start + timedelta(hours=3),
                            location=session.destination,
                            cost=cost,
                            currency=session.budget.currency if session.budget else "INR",
                        )
                    ],
                )
            )
        return Itinerary(
            itinerary_id=str(uuid4()),
            trip_id=session.trip_id,
            currency=session.budget.currency if session.budget else "INR",
            days=days,
        )
