"""Deterministic candidate scoring boundary for itinerary optimization."""

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field

from .itinerary import Itinerary
from .planner import ItineraryVariant


class OptimizationObjective(StrEnum):
    COST = "cost"
    TIME = "time"
    EXPERIENCE = "experience"


class CandidateScore(BaseModel):
    itinerary_id: str
    objective: OptimizationObjective
    cost_score: Decimal = Field(ge=0)
    time_score: Decimal = Field(ge=0)
    experience_score: Decimal = Field(ge=0)
    total_score: Decimal = Field(ge=0)


class DeterministicSolver:
    """Select the best feasible candidate with explainable weighted scoring."""

    def score(self, itinerary: Itinerary, objective: OptimizationObjective) -> CandidateScore:
        cost = itinerary.total_cost
        travel_minutes = Decimal(str(sum(block.duration_minutes for block in itinerary.all_blocks())))
        experience = Decimal(str(len(itinerary.all_blocks() * 10)))
        if objective is OptimizationObjective.COST:
            total = cost
        elif objective is OptimizationObjective.TIME:
            total = travel_minutes
        else:
            total = Decimal("100") - experience
        return CandidateScore(
            itinerary_id=itinerary.itinerary_id,
            objective=objective,
            cost_score=cost,
            time_score=travel_minutes,
            experience_score=experience,
            total_score=max(total, Decimal("0")),
        )

    def rank(self, candidates: list[Itinerary], objective: OptimizationObjective) -> list[tuple[Itinerary, CandidateScore]]:
        scored = [(candidate, self.score(candidate, objective)) for candidate in candidates]
        return sorted(scored, key=lambda item: item[1].total_score)

    def objective_for_variant(self, variant: ItineraryVariant) -> OptimizationObjective:
        return {
            ItineraryVariant.COST_OPTIMIZED: OptimizationObjective.COST,
            ItineraryVariant.TIME_OPTIMIZED: OptimizationObjective.TIME,
            ItineraryVariant.EXPERIENCE_OPTIMIZED: OptimizationObjective.EXPERIENCE,
        }[variant]
