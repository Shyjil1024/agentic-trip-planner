"""Environment-driven runtime configuration."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderSettings:
    transport_url: str | None
    transport_api_key: str | None
    request_timeout_seconds: float
    retry_attempts: int
    database_path: str

    @classmethod
    def from_environment(cls) -> "ProviderSettings":
        return cls(
            transport_url=os.getenv("TRIP_TRANSPORT_URL"),
            transport_api_key=os.getenv("TRIP_TRANSPORT_API_KEY"),
            request_timeout_seconds=float(os.getenv("TRIP_PROVIDER_TIMEOUT", "5")),
            retry_attempts=int(os.getenv("TRIP_PROVIDER_RETRIES", "2")),
            database_path=os.getenv("TRIP_DATABASE_PATH", "trip_planner.sqlite3"),
        )

    @property
    def live_transport_configured(self) -> bool:
        return bool(self.transport_url and self.transport_api_key)
