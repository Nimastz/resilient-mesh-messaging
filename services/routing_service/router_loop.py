# services/routing_service/router_loop.py
# drains the SQLite queue and forwards messages to the BLE adapter with TTL + retry logic.

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from math import pow
from pathlib import Path

import httpx
import yaml

from lib.envelope import MessageEnvelope
from .router_db import get_outgoing, mark_delivered, mark_dropped, increment_retry

CONFIG_PATH = Path("config/routing_config.yaml")
BLE_ADAPTER_URL = "http://localhost:7003/v1/ble/send_chunk"

if CONFIG_PATH.exists():
    with CONFIG_PATH.open() as f:
        ROUTING_CFG = yaml.safe_load(f) or {}
else:
    ROUTING_CFG = {}

MAX_RETRIES = ROUTING_CFG.get("max_retries", 5)
BASE_BACKOFF_MS = ROUTING_CFG.get("base_retry_backoff_ms", 500)
MAX_TTL = ROUTING_CFG.get("max_ttl", 8)


def _parse_timestamp(ts: str) -> datetime:
    # SQLite CURRENT_TIMESTAMP -> 'YYYY-MM-DD HH:MM:SS' (ISO-compatible)
    return datetime.fromisoformat(ts)


def _should_retry(row: dict) -> bool:
    """
    Exponential backoff based on retries + last_update.
    """
    retries = row["retries"]
    last_update = _parse_timestamp(row["last_update"])

    if retries == 0:
        return True

    backoff_ms = BASE_BACKOFF_MS * pow(2, retries - 1)
    elapsed_ms = (
        datetime.now(timezone.utc) - last_update.replace(tzinfo=timezone.utc)
    ).total_seconds() * 1000.0

    return elapsed_ms >= backoff_ms


async def process_outgoing_queue() -> None:
    rows = get_outgoing()
    if not rows:
        return

    async with httpx.AsyncClient() as client:
        for row in rows:
            if not _should_retry(row):
                continue

            row_id = row["row_id"]
            env_json = row["envelope_json"]

            try:
                envelope = MessageEnvelope.parse_raw(env_json)
            except Exception as e:
                print(f"[Routing] invalid envelope JSON for row {row_id}: {e}")
                mark_dropped(row_id, reason="invalid_envelope")
                continue

            # TTL guard (defense in depth)
            if envelope.header.ttl <= 0 or envelope.header.ttl > MAX_TTL:
                print(f"[Routing] dropping msg {envelope.header.msg_id}: TTL expired")
                mark_dropped(row_id, reason="ttl_expired")
                continue

            if row["retries"] >= MAX_RETRIES:
                print(f"[Routing] dropping msg {envelope.header.msg_id}: max_retries exceeded")
                mark_dropped(row_id, reason="max_retries")
                continue

            # Update TTL + hop count before forwarding
            envelope.header.ttl -= 1
            envelope.header.hop_count += 1

            try:
                resp = await client.post(
                    BLE_ADAPTER_URL,
                    json={"chunk": json.loads(envelope.json())},
                    timeout=5.0,
                )
                if resp.status_code == 200:
                    print(f"[Routing] delivered msg {envelope.header.msg_id}")
                    mark_delivered(row_id)
                else:
                    print(
                        f"[Routing] BLE error {resp.status_code} "
                        f"for {envelope.header.msg_id}: {resp.text}"
                    )
                    increment_retry(row_id)

            except Exception as e:
                print(f"[Routing] exception sending msg {envelope.header.msg_id}: {e}")
                increment_retry(row_id)


async def routing_loop(interval_seconds: float = 2.0):
    """
    Background loop polling the routing queue.
    """
    while True:
        await process_outgoing_queue()
        await asyncio.sleep(interval_seconds)
