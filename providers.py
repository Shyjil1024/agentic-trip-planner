"""Provider adapter interfaces and fallback routing."""

from collections.abc import Sequence
from typing import Protocol

from .contracts import ResultStatus, ToolResult, TransportOption
from .domain import TripSession


class TransportProvider(Protocol):
    name: str

    def search(self, session: TripSession) -> ToolResult:
        """Return transport options using the provider's API."""


class ProviderRouter:
    """Try transport providers in order and preserve failure warnings."""

    def __init__(self, providers: Sequence[TransportProvider]) -> None:
        if not providers:
            raise ValueError("at least one transport provider is required")
        self.providers = list(providers)

    def search_transport(self, session: TripSession) -> ToolResult:
        failures: list[str] = []
        for provider in self.providers:
            try:
                result = provider.search(session)
            except Exception as error:
                failures.append(f"{provider.name}: {error}")
                continue
            if result.status is not ResultStatus.FAILED:
                result.warnings.extend(failures)
                return result
            failures.extend(result.warnings or [f"{provider.name} returned failed"])

        return ToolResult(
            status=ResultStatus.FAILED,
            confidence=0,
            warnings=failures or ["all transport providers failed"],
        )


class StaticTransportProvider:
    """Deterministic development adapter for local integration tests."""

    name = "static-development"

    def __init__(self, options: Sequence[TransportOption] | None = None) -> None:
        self.options = list(options or [])

    def search(self, session: TripSession) -> ToolResult:
        return ToolResult(
            status=ResultStatus.SUCCESS if self.options else ResultStatus.PARTIAL,
            confidence=0.5 if self.options else 0.1,
            data={"options": [option.model_dump(mode="json") for option in self.options]},
            assumptions=["static development data; not live availability"],
            warnings=[] if self.options else ["no static transport options configured"],
        )


class RetryingTransportProvider:
    """Retry a provider call before the router moves to its fallback."""

    def __init__(self, provider: TransportProvider, attempts: int = 2) -> None:
        if attempts < 1:
            raise ValueError("attempts must be at least one")
        self.provider = provider
        self.attempts = attempts
        self.name = provider.name

    def search(self, session: TripSession) -> ToolResult:
        failures: list[str] = []
        for _ in range(self.attempts):
            try:
                return self.provider.search(session)
            except Exception as error:
                failures.append(str(error))
        raise RuntimeError(f"{self.name} failed after {self.attempts} attempts: {failures[-1]}")
