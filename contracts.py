"""Structured contracts for specialist agents and provider tools."""

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ResultStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class AgentName(StrEnum):
    TRANSPORT = "transport"
    ACCOMMODATION = "accommodation"
    ACTIVITIES = "activities"
    WEATHER = "weather"
    BUDGET = "budget"
    RISK = "risk"


class SourceReference(BaseModel):
    provider: str = Field(min_length=1)
    retrieved_at: datetime
    reference: str | None = None


class ToolResult(BaseModel):
    """Common envelope returned by every provider tool."""

    status: ResultStatus
    confidence: float = Field(ge=0, le=1)
    data: dict[str, Any] = Field(default_factory=dict)
    sources: list[SourceReference] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class TransportOption(BaseModel):
    origin: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    mode: str = Field(min_length=1)
    departure: datetime
    arrival: datetime
    duration_minutes: int = Field(gt=0)
    transfers: int = Field(default=0, ge=0)
    price: float = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)


class AccommodationOption(BaseModel):
    name: str = Field(min_length=1)
    location: str = Field(min_length=1)
    check_in: date
    check_out: date
    total_price: float = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    cancellation_policy: str | None = None


class ActivityOption(BaseModel):
    name: str = Field(min_length=1)
    location: str = Field(min_length=1)
    duration_minutes: int = Field(gt=0)
    price: float = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class WeatherSnapshot(BaseModel):
    observed_for: date
    condition: str = Field(min_length=1)
    temperature_celsius: float
    precipitation_probability: float = Field(ge=0, le=1)
    severe_weather: bool = False
    source: SourceReference


class RiskAssessment(BaseModel):
    level: Literal["low", "medium", "high"]
    risks: list[str] = Field(default_factory=list)
    mitigations: list[str] = Field(default_factory=list)


class SpecialistResponse(BaseModel):
    """Typed specialist output after interpreting one or more tool results."""

    agent: AgentName
    status: ResultStatus
    confidence: float = Field(ge=0, le=1)
    data: list[Any] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
