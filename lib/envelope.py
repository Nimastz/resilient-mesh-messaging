# lib/envelop.py
from pydantic import BaseModel
from typing import Optional


class EnvelopeHeader(BaseModel):
    sender_fp: str          # fingerprint of sender pubkey
    recipient_fp: str       # fingerprint of recipient pubkey
    msg_id: str             # uuid-v4
    nonce: str              # base64-encoded AES-GCM nonce
    ttl: int                # remaining hops
    hop_count: int = 0      # how many hops taken so far
    ts: int                 # unix timestamp for replay bounds


class ChunkInfo(BaseModel):
    index: int = 0
    total: int = 1


class RoutingMeta(BaseModel):
    priority: str = "normal"    # normal|high|low
    dup_suppress: bool = True


class MessageEnvelope(BaseModel):
    version: str = "1.0"
    header: EnvelopeHeader
    ciphertext: str             # base64 AES-GCM ciphertext (incl. auth tag)
    chunks: ChunkInfo = ChunkInfo()
    routing: RoutingMeta = RoutingMeta()

