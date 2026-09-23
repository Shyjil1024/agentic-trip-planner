from decimal import Decimal

import pytest

from trip_planner import TripSession
from trip_planner.budget import BudgetService


def make_session(constraints=None):
    return TripSession(
        trip_id="trip-1",
        user_id="user-1",
        destination="Ladakh",
        duration_days=7,
        travelers={"adults": 2, "children": 0},
        constraints=constraints or {},
    )


def test_budget_total_uses_decimal_arithmetic():
    breakdown = BudgetService().calculate(
        {"transport": "45000.10", "lodging": 30000, "food": "4999.90"},
        "INR",
    )

    assert breakdown.total == Decimal("80000.00")


def test_negative_budget_categories_are_rejected():
    with pytest.raises(ValueError):
        BudgetService().calculate({"food": -1}, "INR")


def test_budget_limit_violation_is_structured():
    service = BudgetService()
    session = make_session({"hard": {"budget_max": {"amount": 80000, "currency": "INR"}}})

    result = service.validate(session, service.calculate({"total": 80001}, "INR"))

    assert result.valid is False
    assert result.violations[0].code == "BUDGET_EXCEEDED"


def test_currency_mismatch_is_invalid():
    service = BudgetService()
    session = make_session({"hard": {"budget_max": {"amount": 80000, "currency": "INR"}}})

    result = service.validate(session, service.calculate({"total": 100}, "USD"))

    assert result.valid is False
    assert result.violations[0].code == "BUDGET_CURRENCY_MISMATCH"


def test_duration_and_transfer_constraints_are_checked():
    service = BudgetService()
    session = make_session({"hard": {"duration_days": 5, "max_transfers": 1}})

    result = service.validate(session, service.calculate({"total": 100}, "INR"), transfers=2)
    codes = {violation.code for violation in result.violations}

    assert codes == {"DURATION_MISMATCH", "TRANSFERS_EXCEEDED"}


def test_traveler_constraint_is_checked():
    service = BudgetService()
    session = make_session({"hard": {"travelers": {"adults": 1, "children": 0}}})

    result = service.validate(session, service.calculate({"total": 100}, "INR"))

    assert result.violations[0].code == "TRAVELER_COUNT_MISMATCH"
