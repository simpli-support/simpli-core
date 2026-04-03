"""Webhook signature verification for supported platforms.

Each platform signs webhooks differently. This module provides a
unified ``verify_signature()`` function that dispatches to the
correct verification method based on platform name.
"""

from __future__ import annotations

import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)


def verify_signature(
    platform: str,
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """Verify a webhook signature for a given platform.

    Args:
        platform: Platform name (zendesk, freshdesk, intercom, hubspot, jira).
        payload: Raw request body bytes.
        signature: Signature from the platform's signature header.
        secret: Webhook signing secret configured for this platform.

    Returns:
        True if signature is valid, False otherwise.
    """
    verifier = _VERIFIERS.get(platform)
    if verifier is None:
        logger.warning("No signature verifier for platform: %s", platform)
        return False
    return verifier(payload, signature, secret)


def _verify_hmac_sha256(
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """Standard HMAC-SHA256 verification (Zendesk, Freshdesk, Intercom)."""
    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    # Some platforms prefix with "sha256="
    sig = signature.removeprefix("sha256=")
    return hmac.compare_digest(sig, expected)


def _verify_hubspot_v3(
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """HubSpot v3 signature: SHA-256(secret + payload)."""
    hash_input = secret.encode("utf-8") + payload
    expected = hashlib.sha256(hash_input).hexdigest()
    return hmac.compare_digest(signature, expected)


def _verify_jira(
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """Atlassian webhook signature (HMAC-SHA256)."""
    return _verify_hmac_sha256(payload, signature, secret)


def _verify_servicenow(
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """ServiceNow webhook signature (HMAC-SHA256)."""
    return _verify_hmac_sha256(payload, signature, secret)


def _verify_salesforce(
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """Salesforce Platform Event / Outbound Message signature."""
    return _verify_hmac_sha256(payload, signature, secret)


_VERIFIERS: dict[str, type[None] | callable] = {  # type: ignore[type-arg]
    "zendesk": _verify_hmac_sha256,
    "freshdesk": _verify_hmac_sha256,
    "intercom": _verify_hmac_sha256,
    "hubspot": _verify_hubspot_v3,
    "jira": _verify_jira,
    "servicenow": _verify_servicenow,
    "salesforce": _verify_salesforce,
}

# Platform → header name for the signature
SIGNATURE_HEADERS: dict[str, str] = {
    "zendesk": "X-Zendesk-Webhook-Signature",
    "freshdesk": "X-Freshdesk-Webhook-Signature",
    "intercom": "X-Hub-Signature-256",
    "hubspot": "X-HubSpot-Signature-v3",
    "jira": "X-Hub-Signature",
    "servicenow": "X-ServiceNow-Signature",
    "salesforce": "X-Salesforce-Signature",
}
