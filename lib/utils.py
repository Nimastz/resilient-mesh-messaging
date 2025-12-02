# lib/utils.py
"""
Shared helper utilities for the mesh messaging.

Contains:
- Base64 helpers
- Secure random nonce + msg_id generation
- UNIX timestamp helper
- Public-key fingerprint helper
- Convenience function to build a MessageEnvelope skeleton
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

# Default AES-GCM nonce size for this project: 96-bit (12 bytes)
DEFAULT_NONCE_BYTES = 12


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def b64encode(data: bytes) -> str:
    """Return standard base64 (ASCII str) encoding."""
    return base64.b64encode(data).decode("ascii")


def b64decode(data_b64: str) -> bytes:
    """Decode base64 (ASCII str) into bytes."""
    return base64.b64decode(data_b64.encode("ascii"))


def generate_nonce(num_bytes: int = DEFAULT_NONCE_BYTES) -> str:
    """
    Generate a cryptographically secure random nonce and return it base64-encoded.

    Default is 96-bit (12 bytes) for AES-GCM, matching the envelope schema.
    """
    return b64encode(os.urandom(num_bytes))


def generate_msg_id() -> str:
    """
    Generate a UUIDv4 string for msg_id.
    """
    return str(uuid.uuid4())


def current_unix_ts() -> int:
    """
    Return current UNIX timestamp (seconds since epoch, UTC).
    """
    return int(time.time())


def fingerprint_bytes(data: bytes, out_len: int = 32) -> str:
    """
    Compute a SHA-256 based fingerprint of arbitrary binary data, then
    truncate and base64-encode it.

    Used for public-key fingerprints (sender_fp/recipient_fp).
    """
    digest = hashlib.sha256(data).digest()
    truncated = digest[:out_len]
    return b64encode(truncated)


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
    Simple defensive check for TTLs.
    Raises ValueError if invalid.
    """
    if ttl < 0:
        raise ValueError("ttl must be non-negative")


def validate_priority(priority: str) -> None:
    """
    Validate routing priority field.
    """
    if priority not in ("normal", "high", "low"):
        raise ValueError(f"invalid priority: {priority}")
