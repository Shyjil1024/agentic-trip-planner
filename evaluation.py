"""Deterministic benchmark harness for trip-planning scenarios."""

from collections.abc import Callable, Iterable
from decimal import Decimal
from enum import StrEnum
from time import perf_counter

from pydantic import BaseModel, Field

from .validation import ValidationResult


class ScenarioType(StrEnum):
    PLANNING = "planning"
    DISRUPTION = "disruption"
    FAILURE_RECOVERY = "failure_recovery"


class EvaluationScenario(BaseModel):
    name: str = Field(min_length=1)
    scenario_type: ScenarioType
    expected_budget: Decimal | None = None


class ScenarioResult(BaseModel):
    name: str
    passed: bool
    constraint_satisfied: bool = False
    budget_accurate: bool | None = None
    recovery_successful: bool | None = None
    latency_ms: float = 0
    error: str | None = None


class EvaluationReport(BaseModel):
    results: list[ScenarioResult] = Field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(result.passed for result in self.results)

    @property
    def constraint_satisfaction_rate(self) -> float:
        return self._rate(lambda result: result.constraint_satisfied)

    @property
    def budget_accuracy_rate(self) -> float:
        checked = [result for result in self.results if result.budget_accurate is not None]
        return sum(result.budget_accurate for result in checked) / len(checked) if checked else 1.0

    @property
    def recovery_rate(self) -> float:
        checked = [result for result in self.results if result.recovery_successful is not None]
        return sum(result.recovery_successful for result in checked) / len(checked) if checked else 1.0

    def _rate(self, predicate: Callable[[ScenarioResult], bool]) -> float:
        return sum(predicate(result) for result in self.results) / self.total if self.total else 1.0


class ScenarioOutcome(BaseModel):
    validation: ValidationResult | None = None
    reported_budget: Decimal | None = None
    recovery_validation: ValidationResult | None = None


ScenarioRunner = Callable[[EvaluationScenario], ScenarioOutcome]


class EvaluationHarness:
    """Run scenario callbacks and derive comparable deterministic metrics."""

    def run(self, scenarios: Iterable[EvaluationScenario], runner: ScenarioRunner) -> EvaluationReport:
        results: list[ScenarioResult] = []
        for scenario in scenarios:
            started = perf_counter()
            try:
                outcome = runner(scenario)
                constraint_satisfied = bool(outcome.validation and outcome.validation.valid)
                budget_accurate = None
                if scenario.expected_budget is not None:
                    budget_accurate = outcome.reported_budget == scenario.expected_budget
                recovery_successful = None
                if scenario.scenario_type in {ScenarioType.DISRUPTION, ScenarioType.FAILURE_RECOVERY}:
                    recovery_successful = bool(outcome.recovery_validation and outcome.recovery_validation.valid)
                passed = constraint_satisfied and (budget_accurate is not False) and (recovery_successful is not False)
                results.append(
                    ScenarioResult(
                        name=scenario.name,
                        passed=passed,
                        constraint_satisfied=constraint_satisfied,
                        budget_accurate=budget_accurate,
                        recovery_successful=recovery_successful,
                        latency_ms=(perf_counter() - started) * 1000,
                    )
                )
            except Exception as error:
                results.append(
                    ScenarioResult(
                        name=scenario.name,
                        passed=False,
                        error=str(error),
                        latency_ms=(perf_counter() - started) * 1000,
                    )
                )
        return EvaluationReport(results=results)
