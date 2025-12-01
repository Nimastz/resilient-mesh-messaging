# services/routing_service/api.py
from fastapi import FastAPI, HTTPException
from typing import Optional, List

from lib.envelope import MessageEnvelope
from .db import init_db, enqueue_message, get_outgoing, mark_delivered
from .router import routing_loop
from .ids import is_rate_limited, is_duplicate, log_suspicious
import asyncio
import json
from pathlib import Path

IDS_LOG_PATH = Path("routing_suspicious.log")
app = FastAPI()


@app.on_event("startup")
async def startup():
    init_db()
    asyncio.create_task(routing_loop(interval_seconds=2.0))


# helper for standard error format
def error_response(code: str, detail: str, status: int = 400, retryable: bool = False):
    raise HTTPException(
        status_code=status,
        detail={"error": {"code": code, "detail": detail, "retryable": retryable}},
    )


@app.post("/v1/router/enqueue")
def api_enqueue(envelope: MessageEnvelope):
    """
    In:  { <ENVELOPE_JSON> }
    Out: { "queued": true, "msg_id": "uuid" }
    """
    try:
        envelope_json = envelope.json()
        msg_id = envelope.header.msg_id
        ttl = envelope.header.ttl
        enqueue_message(msg_id, envelope_json, ttl)
        return {"queued": True, "msg_id": msg_id}
    except Exception as e:
        error_response("DB_ERROR", f"Failed to enqueue: {e}", status=500)


@app.get("/v1/router/outgoing_chunks")
def api_outgoing(limit: Optional[int] = 50):
    """
    Out: { "items": [ { "chunk": <ENVELOPE_JSON>, "target_peer": "fingerprint" } ] }
    """
    rows = get_outgoing()[: limit or 50]
    items = []
    for row in rows:
        items.append(
            {
                "chunk": row["envelope_json"],
                "target_peer": row["msg_id"],  # placeholder until real peer selection
            }
        )
    return {"items": items}


@app.post("/v1/router/mark_delivered")
def api_mark(payload: dict):
    """
    In:  { "msg_id": "uuid", "chunk_index": 0, "peer": "fingerprint" }
    Out: { "ok": true }
    """
    row_id = payload.get("row_id")
    if row_id is None:
        error_response("INVALID_INPUT", "row_id required")
    mark_delivered(row_id)
    return {"ok": True}


@app.post("/v1/router/on_chunk_received")
def api_on_chunk_received(payload: dict):
    """
    BLE → Router callback.
    In:  { "chunk": <ENVELOPE_JSON>, "link_meta": { "rssi": -55, "peer": "fingerprint" } }
    Out: { "accepted": true|false, "action": "forward|drop|final" }
    Errors:
      - 410 TTL_EXPIRED
      - 200 with accepted:false for DUPLICATE / RATE_LIMITED
    """
    link_meta = payload.get("link_meta") or {}
    peer = link_meta.get("peer", "unknown")

    try:
        env = MessageEnvelope.parse_obj(payload["chunk"])
    except Exception:
        log_suspicious("INVALID_ENVELOPE", peer, "unknown", "failed to parse envelope")
        error_response("INVALID_INPUT", "invalid envelope from BLE")

    msg_id = env.header.msg_id

    # TTL guard on ingress
    if env.header.ttl <= 0:
        log_suspicious("TTL_EXPIRED", peer, msg_id, "received with ttl <= 0")
        raise HTTPException(
            status_code=410,
            detail={"error": {"code": "TTL_EXPIRED", "detail": "ttl <= 0", "retryable": False}},
        )

    # Duplicate detection
    if env.routing.dup_suppress and is_duplicate(msg_id):
        log_suspicious("DUPLICATE", peer, msg_id, "duplicate msg_id seen")
        return {"accepted": False, "action": "drop"}

    # Rate limiting per peer
    if is_rate_limited(peer):
        log_suspicious("RATE_LIMIT", peer, msg_id, "per-peer rate limit exceeded")
        return {"accepted": False, "action": "drop"}

    # For now, we don't enqueue here (that's crypto→router path),
    # we just say it's final (delivered to this node).
    return {"accepted": True, "action": "final"}

@app.get("/v1/router/queue_debug")
def api_queue_debug():
    """
    Simple admin/debug endpoint to view the raw queue.
    """
    return {"items": get_outgoing()}

@app.get("/v1/router/stats")
def api_stats():
    """
    Simple stats for debugging: number of queued, retries, etc.
    """
    rows = get_outgoing()
    total = len(rows)
    retries = sum(r["retries"] for r in rows)
    return {
        "total_queued": total,
        "total_retries": retries,
    }



@app.get("/v1/router/ids_log_tail")
def api_ids_log_tail(limit: int = 50):
    """
    Return last N suspicious IDS events.
    In real system: protect with auth.
    """
    if not IDS_LOG_PATH.exists():
        return {"events": []}

    with IDS_LOG_PATH.open("r", encoding="utf-8") as f:
        lines = f.readlines()[-limit:]

    # Convert JSON-lines to Python dicts
    events = [json.loads(l) for l in lines]

    return {"events": events}