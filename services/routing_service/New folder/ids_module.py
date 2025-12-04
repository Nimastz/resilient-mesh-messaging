# services/routing_service/ids_madule.py
# does per-peer rate limiting + duplicate detection + suspicious logging, configurable via YAML.

"""
Routing IDS / anomaly detection for Person 2.

- Sliding-window rate limiting per peer
- Duplicate msg_id suppression
- Suspicious event logging (plaintext for now, can be encrypted later)
"""

from __future__ import annotations
import hashlib
import json
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Deque, Dict, Set
from .config_loader import ROUTING_CFG
cfg = ROUTING_CFG.get("ids", {})
WINDOW_SECONDS = cfg.get("window_seconds", 5)
MAX_MSGS_PER_WINDOW = cfg.get("max_msgs_per_window", 20)

# in-memory state
_peer_windows: Dict[str, Deque[datetime]] = defaultdict(deque)
_seen_msg_ids: Dict[str, float] = {}
_peer_suspicious_counts = defaultdict(int)
_blocked_peers = {} 
LOG_PATH = Path("routing_suspicious.log")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def is_rate_limited(peer: str) -> bool:
    """
    Sliding-window rate limiting per peer.
    """
    if peer in _blocked_peers:
        return True
    
    window = _peer_windows[peer]
    now = _now()
    cutoff = now - timedelta(seconds=WINDOW_SECONDS)

    # drop old timestamps
    while window and window[0] < cutoff:
        window.popleft()

    if len(window) >= MAX_MSGS_PER_WINDOW:
        return True

    window.append(now)
    return False


def is_duplicate(msg_id: str) -> bool:
    """
    Duplicate detection with TTL-based memory purge.
    """
    ttl_sec = cfg.get("duplicate_suppression_ttl", 600)

    now = _now().timestamp()
    cutoff = now - ttl_sec

    # Purge old msg_ids
    for mid, ts in list(_seen_msg_ids.items()):
        if ts < cutoff:
            del _seen_msg_ids[mid]

    if msg_id in _seen_msg_ids:
        return True

    _seen_msg_ids[msg_id] = now
    return False



def log_suspicious(
    event_type: str,
    peer: str,
    msg_id: str,
    detail: str,
    extra: dict | None = None,
) -> None:
    """
    Log suspicious events as JSON-lines.
     can route this through the crypto service to encrypt
    json.dumps(record) before writing to disk.
    """
    _peer_suspicious_counts[peer] += 1

    limit = cfg.get("block_peer_after", 999999)
    if _peer_suspicious_counts[peer] >= limit:
        _blocked_peers[peer] = _now()
    # cluster events per peer/message without exposing raw identifiers in a stolen log file.
    record = {
        "ts": _now().isoformat(),
        "event": event_type,
        "peer": _anon(peer),
        "msg_id": _anon(msg_id),
        "detail": detail,
        "extra": extra or {},
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _anon(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]

