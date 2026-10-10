"""Deterministic budget calculation and hard-constraint validation."""

from decimal import Decimal
from typing import Mapping

from pydantic import BaseModel, ConfigDict, Field

from .domain import TripSession


class BudgetBreakdown(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    categories: dict[str, Decimal] = Field(default_factory=dict)
    currency: str = Field(min_length=3, max_length=3)

    @property
    def total(self) -> Decimal:
        return sum(self.categories.values(), Decimal("0"))


class ConstraintViolation(BaseModel):
    code: str
    detail: str


class ConstraintCheckResult(BaseModel):
    valid: bool
    violations: list[ConstraintViolation] = Field(default_factory=list)


class BudgetService:
    """Perform money arithmetic and hard checks without LLM involvement."""

    def calculate(self, categories: Mapping[str, int | float | str | Decimal], currency: str) -> BudgetBreakdown:
        normalized = {
            name: self._to_decimal(amount)
            for name, amount in categories.items()
        }
        if any(amount < 0 for amount in normalized.values()):
            raise ValueError("budget category amounts cannot be negative")
        return BudgetBreakdown(categories=normalized, currency=currency.upper())

    def validate(self, session: TripSession, breakdown: BudgetBreakdown, transfers: int = 0) -> ConstraintCheckResult:
        violations: list[ConstraintViolation] = []
        hard = session.constraints.hard

        if hard.budget_max:
            if breakdown.currency != hard.budget_max.currency.upper():
                violations.append(
                    ConstraintViolation(
                        code="BUDGET_CURRENCY_MISMATCH",
                        detail=f"breakdown is {breakdown.currency}, limit is {hard.budget_max.currency.upper()}",
                    )
                )
            elif breakdown.total > self._to_decimal(hard.budget_max.amount):
                violations.append(
                    ConstraintViolation(
                        code="BUDGET_EXCEEDED",
                        detail=f"total {breakdown.total} exceeds limit {self._to_decimal(hard.budget_max.amount)}",
                    )
                )

        if hard.duration_days is not None and session.duration_days != hard.duration_days:
            violations.append(
                ConstraintViolation(
                    code="DURATION_MISMATCH",
                    detail=f"trip duration {session.duration_days} does not match limit {hard.duration_days}",
                )
            )

        if hard.max_transfers is not None and transfers > hard.max_transfers:
            violations.append(
                ConstraintViolation(
                    code="TRANSFERS_EXCEEDED",
                    detail=f"route has {transfers} transfers, limit is {hard.max_transfers}",
                )
            )

        if hard.travelers is not None and session.travelers != hard.travelers:
            violations.append(
                ConstraintViolation(
                    code="TRAVELER_COUNT_MISMATCH",
                    detail="session traveler count does not match the hard constraint",
                )
            )

        return ConstraintCheckResult(valid=not violations, violations=violations)

    @staticmethod
    def _to_decimal(value: int | float | str | Decimal) -> Decimal:
        return Decimal(str(value))
