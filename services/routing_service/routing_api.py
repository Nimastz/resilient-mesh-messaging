# services/routing_service/routing_api.py
# takes envelopes in, checks TTL / IDS, and talks to the DB + router loop.

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional
from .config_loader import ROUTING_CFG
from lib.utils import hash_token 
from lib.envelope import MessageEnvelope
from lib.errors import http_error, ErrorCode
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from lib.auth import DEVICE_FP_HEADER, DEVICE_TOKEN_HEADER, verify_api_token
from .router_db import init_db, enqueue_message, get_outgoing, mark_delivered
from .router_loop import routing_loop
from .ids_module import is_rate_limited, is_duplicate, log_suspicious


IDS_LOG_PATH = Path("routing_suspicious.log")

app = FastAPI()

# ---------------------------------------------------------------------------
# Device auth
# ---------------------------------------------------------------------------

# Simple dev credential for now; in production this would come from a device DB.
DEV_DEVICE_FP = "DEV-ROUTER-CLIENT"
DEV_DEVICE_TOKEN = "dev-router-token"
DEV_DEVICE_TOKEN_HASH = hash_token(DEV_DEVICE_TOKEN)


def require_device_auth(request: Request) -> str:
    """
    Require X-Device-Fp and X-Device-Token headers and verify token.

    Returns the device fingerprint if successful.
    """
    device_fp = request.headers.get(DEVICE_FP_HEADER)
    token = request.headers.get(DEVICE_TOKEN_HEADER)

    if not device_fp or not token:
        raise http_error(
            status_code=401,
            code=ErrorCode.UNAUTHORIZED,
            detail="Missing device auth headers",
            retryable=False,
        )

    # For now we only accept the single dev credential.
    if device_fp != DEV_DEVICE_FP or not verify_api_token(token, DEV_DEVICE_TOKEN_HASH):
        raise http_error(
            status_code=401,
            code=ErrorCode.UNAUTHORIZED,
            detail="Invalid device credentials",
            retryable=False,
        )

    return device_fp


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan handler to replace deprecated @app.on_event("startup").
    Runs once when the app starts.
    """
    init_db()
    asyncio.create_task(routing_loop(interval_seconds=2.0))
    yield
    # optional: add shutdown cleanup here if needed


app = FastAPI(lifespan=lifespan)

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/v1/router/enqueue")
def api_enqueue(
    envelope: MessageEnvelope,
    device_fp: str = Depends(require_device_auth),
):
    msg_id = envelope.header.msg_id
    ttl = envelope.header.ttl

    ttl_min = ROUTING_CFG.get("ttl_min", 1)
    ttl_default = ROUTING_CFG.get("ttl_default", 4)
    ttl_max = ROUTING_CFG.get("max_ttl", 8)

    if ttl is None:
        ttl = ttl_default
        envelope.header.ttl = ttl  

    if ttl < ttl_min or ttl > ttl_max:
        raise http_error(
            400,
            ErrorCode.INVALID_INPUT,
            f"ttl must be between {ttl_min} and {ttl_max}",
            retryable=False,
        )
    envelope.header.ttl = ttl
    envelope_json = envelope.model_dump_json()

    try:
        enqueue_message(msg_id, envelope_json, ttl)
    except Exception as e:
        raise http_error(
            status_code=500,
            code=ErrorCode.DB_ERROR,
            detail=f"Failed to enqueue: {e}",
            retryable=False,
        )
    return {"queued": True, "msg_id": msg_id}


@app.get("/v1/router/outgoing_chunks")
def api_outgoing(
    limit: Optional[int] = 50,
    device_fp: str = Depends(require_device_auth),
):
    """
    Internal API for BLE adapter / router debugging.

    Out:
      {
        "items": [
          {
            "chunk": "<ENVELOPE_JSON_STRING>",
            "target_peer": "fingerprint-or-placeholder"
          },
          ...
        ]
      }
    """
    rows = get_outgoing()[: limit or 50]
    items = []
    for row in rows:
        items.append(
            {
                "chunk": row["envelope_json"],
                # TODO: real peer selection logic later; placeholder for now
                "target_peer": row["msg_id"],
            }
        )
    return {"items": items}


@app.post("/v1/router/mark_delivered")
def api_mark(
    payload: dict,
    device_fp: str = Depends(require_device_auth),
):
    """
    BLE adapter / higher layer tells router a queue row was delivered.

    In:  { "row_id": 123 }
    Out: { "ok": true }

    Errors:
      - 400 INVALID_INPUT (no row_id)
    """
    row_id = payload.get("row_id")
    if row_id is None:
        raise http_error(
            status_code=400,
            code=ErrorCode.INVALID_INPUT,
            detail="row_id required",
            retryable=False,
        )

    mark_delivered(row_id)
    return {"ok": True}


@app.post("/v1/router/on_chunk_received")
def api_on_chunk_received(
    payload: dict,
    device_fp: str = Depends(require_device_auth),
):
    """
    BLE → Router callback for *incoming* wireless chunks.

    In:
      {
        "chunk": <MessageEnvelope JSON>,
        "link_meta": { "rssi": -55, "peer": "fingerprint" }
      }

    Out (normal):
      { "accepted": true|false, "action": "forward|drop|final" }

    Error cases:
      - 400 INVALID_INPUT (bad envelope)
      - 410 TTL_EXPIRED (ttl <= 0)
      - 200 with accepted:false for DUPLICATE / RATE_LIMITED
    """
    link_meta = payload.get("link_meta") or {}
    peer = link_meta.get("peer", "unknown")
    
    try:
        env = MessageEnvelope.model_validate(payload["chunk"])
    except Exception:
        log_suspicious("INVALID_ENVELOPE", peer, "unknown", "failed to parse envelope")
        raise http_error(
            status_code=400,
            code=ErrorCode.INVALID_INPUT,
            detail="invalid envelope from BLE",
            retryable=False,
        )

    msg_id = env.header.msg_id

    # TTL guard on ingress (defense in depth with router TTL checks)
    if env.header.ttl <= 0:
        log_suspicious("TTL_EXPIRED", peer, msg_id, "received with ttl <= 0")
        raise http_error(
            status_code=410,
            code=ErrorCode.TTL_EXPIRED,
            detail="ttl <= 0",
            retryable=False,
        )

    # Duplicate detection
    if env.routing.dup_suppress and is_duplicate(msg_id):
        log_suspicious("DUPLICATE", peer, msg_id, "duplicate msg_id seen")
        # Not an HTTP error – this is expected behavior, we just tell BLE "drop it"
        return {"accepted": False, "action": "drop"}

    # Rate limiting per peer
    if is_rate_limited(peer):
        log_suspicious("RATE_LIMIT", peer, msg_id, "per-peer rate limit exceeded")
        # Again, logical drop, not an HTTP failure
        return {"accepted": False, "action": "drop"}

    # Phase-1 behavior: final delivery to this node only.
    # Phase-2 multi-hop behavior with one config flag.
    # Phase-2/3 could enqueue for multi-hop forwarding.
    if ROUTING_CFG.get("forwarding_enabled", False):
        return {"accepted": True, "action": "forward"}
    else:
        return {"accepted": True, "action": "final"}


@app.get("/v1/router/queue_debug")
def api_queue_debug(
    device_fp: str = Depends(require_device_auth),
):
    """
    Admin/debug endpoint to inspect the raw queue rows.
    """
    return {"items": get_outgoing()}


@app.get("/v1/router/stats")
def api_stats(
    device_fp: str = Depends(require_device_auth),
):
    """
    Simple stats endpoint for UI / metrics:
      - total_queued
      - total_retries
    """
    rows = get_outgoing()
    total = len(rows)
    retries = sum(r["retries"] for r in rows)
    return {"total_queued": total, "total_retries": retries}


@app.get("/v1/router/ids_log_tail")
def api_ids_log_tail(
    limit: int = 50,
    device_fp: str = Depends(require_device_auth),
):
    """
    Return last N suspicious IDS events (JSON-lines file).

    In a real system this must be protected with auth; we require the
    same device auth as other endpoints.
    """
    if not IDS_LOG_PATH.exists():
        return {"events": []}

    with IDS_LOG_PATH.open("r", encoding="utf-8") as f:
        lines = f.readlines()[-limit:]

    events = [json.loads(l) for l in lines]
    return {"events": events}