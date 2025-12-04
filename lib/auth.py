# lib/auth.py
"""
Authentication helpers for device ↔ service communication.

This module centralizes:
- Device API token generation (high-entropy random string).
- Hashing and verification of tokens.
- Header name constants used by services.
"""

from __future__ import annotations
import hmac
from dataclasses import dataclass

# Use relative import because we're inside the `lib` package
from .utils import generate_api_token, hash_token

# ---------------------------------------------------------------------------
# Header names (shared across services)
# ---------------------------------------------------------------------------

DEVICE_FP_HEADER = "X-Device-Fp"
DEVICE_TOKEN_HEADER = "X-Device-Token"


@dataclass
class DeviceApiCredentials:
    """
    Represents a device API credential pair.

    device_fp:
        Opaque device fingerprint / identifier. May be random or derived
        from hardware attestation at provisioning time.
    token_hash:
        SHA-256 hash of the device's API token.
    """
    device_fp: str
    token_hash: str


def create_device_token(device_fp: str) -> tuple[str, DeviceApiCredentials]:
    """
    Create a new API token for a device.

    Returns:
        (plaintext_token, DeviceApiCredentials)

    You should persist DeviceApiCredentials.token_hash server-side
    (e.g. in a DB row for this device), and show the plaintext token
    to the client exactly once.
    """
    token = generate_api_token()
    token_hash = hash_token(token)
    creds = DeviceApiCredentials(device_fp=device_fp, token_hash=token_hash)
    return token, creds


def verify_api_token(token: str, expected_hash: str) -> bool:
    """
    Verify a token against a stored hash using a constant-time comparison.

    Returns:
        True if token matches the expected hash, False otherwise.
    """
    if not token:
        return False
    computed = hash_token(token)
    # Use constant-time comparison to avoid timing leaks.
    return hmac.compare_digest(computed, expected_hash)
