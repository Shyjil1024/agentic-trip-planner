"""Typed itinerary structures used by validation and replanning."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ItineraryBlock(BaseModel):
    block_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    date: date
    start: datetime
    end: datetime
    location: str = Field(min_length=1)
    cost: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(min_length=3, max_length=3)

    @property
    def duration_minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)


class ItineraryDay(BaseModel):
    date: date
    blocks: list[ItineraryBlock] = Field(default_factory=list)

    @property
    def total_cost(self) -> Decimal:
        return sum((block.cost for block in self.blocks), Decimal("0"))


class Itinerary(BaseModel):
    itinerary_id: str = Field(min_length=1)
    trip_id: str = Field(min_length=1)
    currency: str = Field(min_length=3, max_length=3)
    days: list[ItineraryDay] = Field(default_factory=list)

    @property
    def total_cost(self) -> Decimal:
        return sum((day.total_cost for day in self.days), Decimal("0"))

    def all_blocks(self) -> list[ItineraryBlock]:
        return [block for day in self.days for block in day.blocks]
