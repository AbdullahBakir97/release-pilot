"""GitHub webhook signature verification using HMAC-SHA256."""

from __future__ import annotations

import hashlib
import hmac

__all__ = ["WebhookVerifier"]


class WebhookVerifier:
    """Verifies GitHub webhook payloads against the X-Hub-Signature-256 header.

    Uses constant-time comparison to prevent timing attacks.
    """

    def __init__(self, secret: str) -> None:
        self._secret = secret.encode()

    def verify(self, payload: bytes, signature: str) -> bool:
        """Verify that *payload* matches the provided HMAC *signature*.

        Args:
            payload: Raw request body bytes.
            signature: Value of the ``X-Hub-Signature-256`` header.

        Returns:
            ``True`` when the signature is valid, ``False`` otherwise.
        """
        if not signature.startswith("sha256="):
            return False
        expected = "sha256=" + hmac.new(self._secret, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
