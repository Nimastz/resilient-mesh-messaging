# lib/utils.py
"""
Shared helper utilities for the mesh messaging.

Contains:
- Base64 helpers
- Secure random nonce + msg_id generation
- UNIX timestamp helper
- Public-key fingerprint helper
- Convenience function to build a MessageEnvelope skeleton
- TTL / priority validation helpers
- Secure token helpers for per-device API auth
"""

from __future__ import annotations

import base64
import hashlib
import os
import time
import uuid
from typing import Optional

from .envelope import (
    MessageEnvelope,
    EnvelopeHeader,
    ChunkInfo,
    RoutingMeta,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default AES-GCM nonce size for this project: 96-bit (12 bytes)
DEFAULT_NONCE_BYTES = 12

# TTL bounds (defensive, fail-closed)
# We allow 0 so that a message can be "delivered locally" but never forwarded.
MIN_TTL = 0
MAX_TTL = 32  # enough for multi-hop, small enough to limit abuse

ALLOWED_PRIORITIES = {"low", "normal", "high"}


# ---------------------------------------------------------------------------
# Base64 helpers
# ---------------------------------------------------------------------------

def b64encode(data: bytes) -> str:
    """Return standard base64 (ASCII str) encoding."""
    return base64.b64encode(data).decode("ascii")


def b64decode(data_b64: str) -> bytes:
    """Decode base64 (ASCII str) into bytes."""
    return base64.b64decode(data_b64.encode("ascii"))


# ---------------------------------------------------------------------------
# Random IDs / timestamps
# ---------------------------------------------------------------------------

def generate_nonce(num_bytes: int = DEFAULT_NONCE_BYTES) -> str:
    """
    Generate a cryptographically secure random nonce and return it base64-encoded.

    Default is 96-bit (12 bytes) for AES-GCM, matching the envelope schema.
    """
    return b64encode(os.urandom(num_bytes))


def generate_msg_id() -> str:
    """Generate a UUIDv4 string for msg_id."""
    return str(uuid.uuid4())


def current_unix_ts() -> int:
    """Return current UNIX timestamp (seconds since epoch, UTC)."""
    return int(time.time())


# ---------------------------------------------------------------------------
# Fingerprints / tokens
# ---------------------------------------------------------------------------

def fingerprint_bytes(data: bytes, out_len: int = 32) -> str:
    """
    Compute a SHA-256 based fingerprint of arbitrary binary data, then
    truncate and base64-encode it.

    Used for public-key fingerprints (sender_fp/recipient_fp).
    """
    digest = hashlib.sha256(data).digest()
    truncated = digest[:out_len]
    return b64encode(truncated)


def generate_api_token(num_bytes: int = 32) -> str:
    """
    Generate a high-entropy API token for authenticating a device to a service.

    Returns a URL-safe base64 string without padding. The *plaintext* token
    should be shown only once to the client; services should store only a hash.
    """
    raw = os.urandom(num_bytes)
    token = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return token


def hash_token(token: str) -> str:
    """
    Compute a SHA-256 hash of an API token.

    We store only the hex-encoded hash server-side; the plaintext token
    is held by the client. This avoids leaking secrets in logs/dumps.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Envelope helpers
# ---------------------------------------------------------------------------

def build_envelope(
    *,
    sender_fp: str,
    recipient_fp: str,
    ciphertext_b64: str,
    ttl: int,
    priority: str = "normal",
    dup_suppress: bool = True,
    chunk_index: int = 0,
    chunk_total: int = 1,
    nonce_b64: Optional[str] = None,
    msg_id: Optional[str] = None,
    ts: Optional[int] = None,
) -> MessageEnvelope:
    """
    Convenience helper to construct a MessageEnvelope instance
    from the core fields. This keeps all three services consistent
    with the Day-0 JSON envelope contract.

    It does NOT perform encryption itself – ciphertext_b64 should already
    contain AES-GCM ciphertext+tag encoded in base64.
    """

    if nonce_b64 is None:
        nonce_b64 = generate_nonce()
    if msg_id is None:
        msg_id = generate_msg_id()
    if ts is None:
        ts = current_unix_ts()

    header = EnvelopeHeader(
        sender_fp=sender_fp,
        recipient_fp=recipient_fp,
        msg_id=msg_id,
        nonce=nonce_b64,
        ttl=ttl,
        hop_count=0,
        ts=ts,
    )

    chunks = ChunkInfo(index=chunk_index, total=chunk_total)
    routing = RoutingMeta(priority=priority, dup_suppress=dup_suppress)

    return MessageEnvelope(
        version="1.0",
        header=header,
        ciphertext=ciphertext_b64,
        chunks=chunks,
        routing=routing,
    )


def validate_ttl(ttl: int) -> None:
    """
    Defensive check for TTLs (remaining hops).

    - Must be an int
    - Must be between MIN_TTL and MAX_TTL inclusive

    Raises ValueError if invalid.
    """
    if not isinstance(ttl, int):
        raise ValueError("ttl must be an integer")
    if ttl < MIN_TTL or ttl > MAX_TTL:
        raise ValueError(f"ttl must be between {MIN_TTL} and {MAX_TTL} (got {ttl})")


def validate_priority(priority: str) -> None:
    """
    Validate routing priority field (fail-closed).

    Raises ValueError if invalid.
    """
    if priority not in ALLOWED_PRIORITIES:
        raise ValueError(f"invalid priority: {priority!r}, allowed={sorted(ALLOWED_PRIORITIES)}")
