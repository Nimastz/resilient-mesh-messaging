# services/routing_service/ids.py
# This covers “encrypted logging” conceptually – the log file is already isolated. 
# Later you can replace the write with a call to Person-3’s crypto service to encrypt json.dumps(record) before writing.
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from typing import Deque, Dict, Set
import json
from pathlib import Path
import yaml

# Load config
CONFIG_PATH = Path("routing_config.yaml")
if CONFIG_PATH.exists():
    with CONFIG_PATH.open() as f:
        cfg = yaml.safe_load(f).get("ids", {})
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
    if msg_id in _seen_msg_ids:
        return True
    _seen_msg_ids.add(msg_id)
    return False


def log_suspicious(event_type: str, peer: str, msg_id: str, detail: str, extra: dict | None = None):
    """
    Suspicious log. For now it's plaintext → in Phase 3 you can pipe this
    through Crypto service for encrypted logging.
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
