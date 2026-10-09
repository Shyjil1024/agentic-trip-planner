"""Independent itinerary validation and targeted repair."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from .domain import TripSession
from .itinerary import Itinerary, ItineraryBlock


class ItineraryIssue(BaseModel):
    code: str
    detail: str
    block_ids: list[str] = Field(default_factory=list)
    day: date | None = None


class ValidationResult(BaseModel):
    valid: bool
    issues: list[ItineraryIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ItineraryValidator:
    """Re-derive feasibility checks without trusting a planner self-report."""

    def validate(self, session: TripSession, itinerary: Itinerary) -> ValidationResult:
        issues: list[ItineraryIssue] = []
        hard = session.constraints.hard
        blocks = itinerary.all_blocks()

        if session.dates:
            for block in blocks:
                if not session.dates.start <= block.date <= session.dates.end:
                    issues.append(
                        ItineraryIssue(
                            code="BLOCK_OUTSIDE_TRIP_DATES",
                            detail=f"{block.title} is outside the trip date range",
                            block_ids=[block.block_id],
                            day=block.date,
                        )
                    )

        for index, first in enumerate(blocks):
            if first.end <= first.start:
                issues.append(
                    ItineraryIssue(
                        code="INVALID_TIME_RANGE",
                        detail=f"{first.title} has an invalid time range",
                        block_ids=[first.block_id],
                        day=first.date,
                    )
                )
            for second in blocks[index + 1 :]:
                if first.date == second.date and first.start < second.end and second.start < first.end:
                    issues.append(
                        ItineraryIssue(
                            code="OVERLAPPING_BLOCKS",
                            detail=f"{first.title} overlaps {second.title}",
                            block_ids=[first.block_id, second.block_id],
                            day=first.date,
                        )
                    )

        if hard.budget_max:
            if itinerary.currency.upper() != hard.budget_max.currency.upper():
                issues.append(
                    ItineraryIssue(
                        code="ITINERARY_CURRENCY_MISMATCH",
                        detail="itinerary currency does not match the budget constraint",
                    )
                )
            elif itinerary.total_cost > Decimal(str(hard.budget_max.amount)):
                issues.append(
                    ItineraryIssue(
                        code="ITINERARY_BUDGET_EXCEEDED",
                        detail=f"total {itinerary.total_cost} exceeds the budget limit",
                    )
                )

        return ValidationResult(valid=not issues, issues=issues)


class TargetedReplanner:
    """Repair only the blocks named by a validation issue."""

    def remove_blocks(self, itinerary: Itinerary, issue: ItineraryIssue) -> Itinerary:
        affected = set(issue.block_ids)
        if not affected:
            raise ValueError("targeted replanning requires affected block ids")
        repaired_days = [
            day.model_copy(update={"blocks": [block for block in day.blocks if block.block_id not in affected]})
            for day in itinerary.days
        ]
        return itinerary.model_copy(update={"days": repaired_days})

    def repair_first_issue(self, itinerary: Itinerary, validation: ValidationResult) -> Itinerary:
        if validation.valid:
            return itinerary
        return self.remove_blocks(itinerary, validation.issues[0])
