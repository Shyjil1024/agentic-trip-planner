"""Security helpers for webhook authenticity and booking gates."""

import hashlib
import hmac


class WebhookVerifier:
    def __init__(self, secret: str) -> None:
        if not secret:
            raise ValueError("webhook secret is required")
        self.secret = secret.encode("utf-8")

    def signature(self, payload: bytes) -> str:
        return hmac.new(self.secret, payload, hashlib.sha256).hexdigest()

    def verify(self, payload: bytes, supplied_signature: str) -> bool:
        expected = self.signature(payload)
        return hmac.compare_digest(expected, supplied_signature)
