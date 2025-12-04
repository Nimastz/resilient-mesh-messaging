# lib/envelope.py
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class EnvelopeHeader(BaseModel):
    """
    Header fields that are visible to routing & BLE, but contain
    no plaintext application data.

    sender_fp / recipient_fp:
        Fingerprints of sender/recipient long-term public keys.
    msg_id:
        UUIDv4 string uniquely identifying this logical message.
    nonce:
        Base64-encoded AES-GCM nonce (96 bits recommended).
    ttl:
        Remaining hops; decremented at each forward.
    hop_count:
        How many hops taken so far.
    ts:
        Unix timestamp for replay detection and freshness bounds.
    """
    sender_fp: str          # fingerprint of sender pubkey
    recipient_fp: str       # fingerprint of recipient pubkey
    msg_id: str             # uuid-v4
    nonce: str              # base64-encoded AES-GCM nonce
    ttl: int                # remaining hops (validated by utils.validate_ttl)
    hop_count: int = 0      # how many hops taken so far
    ts: int                 # unix timestamp for replay bounds


class ChunkInfo(BaseModel):
    """
    Chunking metadata for BLE / transport.

    index:
        0-based index of this chunk.
    total:
        Total number of chunks for this message.
    """
    index: int = 0
    total: int = 1


class RoutingMeta(BaseModel):
    """
    Routing hints that don't affect cryptographic security.

    priority:
        "normal" | "high" | "low"
    dup_suppress:
        Whether intermediate hops should attempt duplicate suppression.
    """
    priority: str = "normal"    # normal|high|low
    dup_suppress: bool = True


class MessageEnvelope(BaseModel):
    """
    Top-level envelope passed between services and sent over BLE.

    version:
        Schema version, currently "1.0".
    header:
        EnvelopeHeader metadata.
    ciphertext:
        Base64-encoded AES-GCM ciphertext (incl. auth tag).
    chunks:
        ChunkInfo for BLE fragmentation.
    routing:
        RoutingMeta hints.
    """
    version: str = "1.0"
    header: EnvelopeHeader
    ciphertext: str             # base64 AES-GCM ciphertext (incl. auth tag)
    chunks: ChunkInfo = ChunkInfo()
    routing: RoutingMeta = RoutingMeta()
