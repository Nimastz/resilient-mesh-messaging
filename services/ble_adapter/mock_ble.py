# ble_adapter/mock_ble.py
from __future__ import annotations
import json
from typing import Dict
from fastapi import FastAPI
from pydantic import BaseModel
from lib.envelope import MessageEnvelope
from lib.utils import validate_ttl, validate_priority

app = FastAPI(title="Mock BLE Adapter")


class SendChunkPayload(BaseModel):
    """
    Payload shape expected by the BLE send_chunk adapter.

    This mirrors the real BLE service contract:
      {
        "chunk": <MessageEnvelope JSON>,
        "target_peer": "<recipient_fp string>"
      }
    """
    chunk: Dict
    target_peer: str


@app.post("/v1/ble/send_chunk")
def receive_chunk(payload: SendChunkPayload):
    """
    Mock BLE endpoint for local debugging.

    - Validates the MessageEnvelope using Pydantic.
    - Validates TTL & priority (fail-closed).
    - Logs a nicely formatted summary to stdout.
    - Always returns `{"queued": true, "estimate_ms": ...}`.
    """
    # Validate and parse the envelope
    try:
        envelope = MessageEnvelope(**payload.chunk)
    except Exception as exc:
        # In a true mock we might just print the error; here we still
        # try to be informative but keep the behavior simple.
        print("[MOCK BLE] Invalid MessageEnvelope:", exc)
        return {"queued": False, "error": "invalid envelope"}

    # Defensive checks (same as real service) – useful to catch bugs in dev
    try:
        validate_ttl(envelope.header.ttl)
        validate_priority(envelope.routing.priority)
    except ValueError as exc:
        print("[MOCK BLE] Invalid TTL/priority:", exc)
        return {"queued": False, "error": str(exc)}

    # Pretty-print a redacted view (no ciphertext content, just length)
    safe_dict = envelope.model_dump()
    # Optionally redact ciphertext length instead of full blob to avoid spam
    safe_dict["ciphertext"] = f"<base64 ciphertext, len={len(envelope.ciphertext)}>"

    print("[MOCK BLE] Received chunk for target_peer:", payload.target_peer)
    print(json.dumps(safe_dict, indent=2))

    # Simulate some network latency estimate
    estimate_ms = 150

    return {"queued": True, "estimate_ms": estimate_ms}
