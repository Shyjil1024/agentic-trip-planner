from trip_planner.config import ProviderSettings
from trip_planner.providers import RetryingTransportProvider


class FailingProvider:
    name = "failing"

    def __init__(self):
        self.calls = 0

    def search(self, session):
        self.calls += 1
        raise RuntimeError("temporary outage")


def test_provider_settings_read_environment(monkeypatch):
    monkeypatch.setenv("TRIP_TRANSPORT_URL", "https://provider.example/search")
    monkeypatch.setenv("TRIP_TRANSPORT_API_KEY", "test-key")
    monkeypatch.setenv("TRIP_PROVIDER_TIMEOUT", "7")
    monkeypatch.setenv("TRIP_PROVIDER_RETRIES", "3")

    settings = ProviderSettings.from_environment()

    assert settings.live_transport_configured
    assert settings.request_timeout_seconds == 7
    assert settings.retry_attempts == 3


def test_retrying_provider_retries_configured_times():
    provider = FailingProvider()
    retrying = RetryingTransportProvider(provider, attempts=3)

    try:
        retrying.search(None)
    except RuntimeError as error:
        assert "3 attempts" in str(error)
    else:
        raise AssertionError("expected provider failure")
    assert provider.calls == 3
