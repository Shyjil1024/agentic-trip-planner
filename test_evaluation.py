from decimal import Decimal

from trip_planner.evaluation import (
    EvaluationHarness,
    EvaluationScenario,
    ScenarioOutcome,
    ScenarioType,
)
from trip_planner.validation import ValidationResult


def test_evaluation_report_calculates_planning_metrics():
    scenarios = [
        EvaluationScenario(
            name="budget-trip",
            scenario_type=ScenarioType.PLANNING,
            expected_budget=Decimal("80000"),
        ),
        EvaluationScenario(name="family-trip", scenario_type=ScenarioType.PLANNING),
    ]

    report = EvaluationHarness().run(
        scenarios,
        lambda scenario: ScenarioOutcome(
            validation=ValidationResult(valid=True),
            reported_budget=Decimal("80000") if scenario.name == "budget-trip" else None,
        ),
    )

    assert report.total == 2
    assert report.passed == 2
    assert report.constraint_satisfaction_rate == 1.0
    assert report.budget_accuracy_rate == 1.0


def test_evaluation_report_measures_recovery_failure():
    scenario = EvaluationScenario(name="flight-delay", scenario_type=ScenarioType.DISRUPTION)

    report = EvaluationHarness().run(
        [scenario],
        lambda item: ScenarioOutcome(
            validation=ValidationResult(valid=True),
            recovery_validation=ValidationResult(valid=False),
        ),
    )

    assert report.passed == 0
    assert report.recovery_rate == 0.0


def test_runner_errors_are_recorded_as_failed_scenarios():
    scenario = EvaluationScenario(name="provider-outage", scenario_type=ScenarioType.FAILURE_RECOVERY)

    report = EvaluationHarness().run([scenario], lambda item: (_ for _ in ()).throw(RuntimeError("provider down")))

    assert report.results[0].passed is False
    assert report.results[0].error == "provider down"
