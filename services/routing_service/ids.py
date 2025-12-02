# services/routing_service/ids.py
# test: pytest services/routing_service/tests/test_ids.py -v

"""
Routing IDS / anomaly detection for Person 2.

- Sliding-window rate limiting per peer
- Duplicate msg_id suppression
- Suspicious event logging (plaintext for now, can be encrypted later)
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Deque, Dict, Set

import yaml

# Load config from same folder as routing config
CONFIG_PATH = Path("config/routing_config.yaml")
if CONFIG_PATH.exists():
    with CONFIG_PATH.open() as f:
        cfg_root = yaml.safe_load(f) or {}
        cfg = cfg_root.get("ids", {})
else:
    cfg = {}

WINDOW_SECONDS = cfg.get("window_seconds", 5)
MAX_MSGS_PER_WINDOW = cfg.get("max_msgs_per_window", 20)

# in-memory state
_peer_windows: Dict[str, Deque[datetime]] = defaultdict(deque)
_seen_msg_ids: Set[str] = set()

LOG_PATH = Path("routing_suspicious.log")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def is_rate_limited(peer: str) -> bool:
    """
    Sliding-window rate limiting per peer.
    """
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
    Simple in-memory duplicate detection by msg_id.
    """
    if msg_id in _seen_msg_ids:
        return True
    _seen_msg_ids.add(msg_id)
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

    Later you can route this through the crypto service to encrypt
    `json.dumps(record)` before writing to disk.
    """
    record = {
        "ts": _now().isoformat(),
        "event": event_type,
        "peer": peer,
        "msg_id": msg_id,
        "detail": detail,
        "extra": extra or {},
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
