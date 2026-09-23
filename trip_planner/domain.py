"""Typed domain state shared by the trip-planning workflow."""

from datetime import date
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TripStatus(StrEnum):
    INTERVIEWING = "interviewing"
    RESEARCHING = "researching"
    PLANNING = "planning"
    VALIDATING = "validating"
    REPLANNING = "replanning"
    LIVE = "live"
    COMPLETED = "completed"


class Location(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    country: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class DateRange(BaseModel):
    start: date
    end: date

    @model_validator(mode="after")
    def validate_order(self) -> "DateRange":
        if self.end < self.start:
            raise ValueError("end date must be on or after start date")
        return self

    @property
    def duration_days(self) -> int:
        return (self.end - self.start).days + 1


class TravelerCount(BaseModel):
    adults: int = Field(default=1, ge=1)
    children: int = Field(default=0, ge=0)

    @property
    def total(self) -> int:
        return self.adults + self.children


class Budget(BaseModel):
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)


class HardConstraints(BaseModel):
    budget_max: Optional[Budget] = None
    duration_days: Optional[int] = Field(default=None, ge=1)
    max_transfers: Optional[int] = Field(default=None, ge=0)
    travelers: Optional[TravelerCount] = None


class Constraints(BaseModel):
    hard: HardConstraints = Field(default_factory=HardConstraints)
    soft: dict[str, object] = Field(default_factory=dict)


class TripSession(BaseModel):
    """The minimum durable state needed to begin the interview workflow."""

    model_config = ConfigDict(str_strip_whitespace=True)

    trip_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    origin: Optional[Location] = None
    dates: Optional[DateRange] = None
    duration_days: Optional[int] = Field(default=None, ge=1)
    travelers: TravelerCount = Field(default_factory=TravelerCount)
    travelers_confirmed: bool = False
    budget: Optional[Budget] = None
    constraints: Constraints = Field(default_factory=Constraints)
    activities: list[str] = Field(default_factory=list)
    current_location: Optional[Location] = None
    status: TripStatus = TripStatus.INTERVIEWING

    @model_validator(mode="after")
    def validate_duration(self) -> "TripSession":
        if self.dates and self.duration_days is not None:
            if self.dates.duration_days != self.duration_days:
                raise ValueError("duration_days must match the supplied date range")
        return self
