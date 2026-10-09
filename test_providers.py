from trip_planner.contracts import ResultStatus, ToolResult, TransportOption
from trip_planner.domain import TripSession
from trip_planner.providers import ProviderRouter, StaticTransportProvider


class BrokenProvider:
    name = "broken"

    def search(self, session):
        raise RuntimeError("timeout")


class FailedProvider:
    name = "failed"

    def search(self, session):
        return ToolResult(status=ResultStatus.FAILED, confidence=0, warnings=["provider unavailable"])


class GoodProvider:
    name = "good"

    def search(self, session):
        return ToolResult(status=ResultStatus.SUCCESS, confidence=0.8, data={"options": []})


def make_session():
    return TripSession(trip_id="trip-1", user_id="user-1", destination="Ladakh")


def test_router_falls_back_after_provider_exception():
    result = ProviderRouter([BrokenProvider(), GoodProvider()]).search_transport(make_session())

    assert result.status is ResultStatus.SUCCESS
    assert result.warnings == ["broken: timeout"]


def test_router_falls_back_after_failed_result():
    result = ProviderRouter([FailedProvider(), GoodProvider()]).search_transport(make_session())

    assert result.status is ResultStatus.SUCCESS
    assert result.warnings == ["provider unavailable"]


def test_router_returns_structured_failure_when_all_providers_fail():
    result = ProviderRouter([BrokenProvider(), FailedProvider()]).search_transport(make_session())

    assert result.status is ResultStatus.FAILED
    assert result.confidence == 0
    assert result.warnings == ["broken: timeout", "provider unavailable"]


def test_static_provider_returns_typed_option_data():
    option = TransportOption(
        origin="Delhi",
        destination="Leh",
        mode="flight",
        departure="2026-10-01T08:00:00",
        arrival="2026-10-01T10:00:00",
        duration_minutes=120,
        price=12000,
        currency="INR",
    )
    result = StaticTransportProvider([option]).search(make_session())

    assert result.status is ResultStatus.SUCCESS
    assert result.data["options"][0]["destination"] == "Leh"
