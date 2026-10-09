"""Human approval gate for booking actions."""

from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field

from .itinerary import Itinerary


class BookingStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


class BookingRequest(BaseModel):
    booking_id: str = Field(default_factory=lambda: str(uuid4()))
    trip_id: str
    itinerary_id: str
    status: BookingStatus = BookingStatus.PENDING_APPROVAL
    items: list[str] = Field(default_factory=list)


class BookingApprovalService:
    """Prepare bookings; never execute payment without explicit approval."""

    def prepare(self, itinerary: Itinerary) -> BookingRequest:
        return BookingRequest(
            trip_id=itinerary.trip_id,
            itinerary_id=itinerary.itinerary_id,
            items=[block.title for block in itinerary.all_blocks()],
        )

    def approve(self, request: BookingRequest, approved: bool) -> BookingRequest:
        return request.model_copy(
            update={"status": BookingStatus.APPROVED if approved else BookingStatus.REJECTED}
        )
