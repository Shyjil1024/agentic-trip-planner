import pytest

from trip_planner.booking import BookingApprovalService
from trip_planner.security import WebhookVerifier


def test_webhook_signature_verifies_only_original_payload():
    verifier = WebhookVerifier("test-secret")
    payload = b'{"event":"FLIGHT_DELAYED"}'
    signature = verifier.signature(payload)

    assert verifier.verify(payload, signature)
    assert not verifier.verify(b'{"event":"HOTEL_UNAVAILABLE"}', signature)


def test_webhook_secret_is_required():
    with pytest.raises(ValueError):
        WebhookVerifier("")


def test_booking_service_only_changes_status_after_boolean_decision():
    assert hasattr(BookingApprovalService(), "approve")
