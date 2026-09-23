from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from trip_planner.contracts import (
    AccommodationOption,
    ActivityOption,
    AgentName,
    ResultStatus,
    RiskAssessment,
    SourceReference,
    SpecialistResponse,
    TransportOption,
    WeatherSnapshot,
)


SOURCE = SourceReference(
    provider="test-provider",
    retrieved_at=datetime(2026, 9, 23, tzinfo=timezone.utc),
)


def test_transport_contract_carries_feasibility_fields():
    option = TransportOption(
        origin="Delhi",
        destination="Leh",
        mode="flight",
        departure=datetime(2026, 10, 1, 8),
        arrival=datetime(2026, 10, 1, 10),
        duration_minutes=120,
        transfers=0,
        price=12000,
        currency="INR",
    )

    assert option.duration_minutes == 120
    assert option.transfers == 0


def test_specialist_response_preserves_partial_status_and_sources():
    response = SpecialistResponse(
        agent=AgentName.WEATHER,
        status=ResultStatus.PARTIAL,
        confidence=0.65,
        data=[WeatherSnapshot(
            observed_for=date(2026, 10, 1),
            condition="clear",
            temperature_celsius=12,
            precipitation_probability=0.1,
            source=SOURCE,
        )],
        sources=[SOURCE],
        warnings=["forecast horizon is limited"],
    )

    assert response.status is ResultStatus.PARTIAL
    assert response.sources[0].provider == "test-provider"
    assert response.data[0].condition == "clear"


def test_specialist_payloads_validate_required_data():
    accommodation = AccommodationOption(
        name="Leh Guest House",
        location="Leh",
        check_in=date(2026, 10, 1),
        check_out=date(2026, 10, 3),
        total_price=6000,
        currency="INR",
    )
    activity = ActivityOption(
        name="Shanti Stupa",
        location="Leh",
        duration_minutes=90,
        price=0,
        currency="INR",
    )
    risk = RiskAssessment(level="medium", risks=["altitude"], mitigations=["acclimatize"])

    assert accommodation.total_price == 6000
    assert activity.duration_minutes == 90
    assert risk.mitigations == ["acclimatize"]


def test_confidence_must_be_between_zero_and_one():
    with pytest.raises(ValidationError):
        SpecialistResponse(agent=AgentName.RISK, status=ResultStatus.SUCCESS, confidence=1.1)
