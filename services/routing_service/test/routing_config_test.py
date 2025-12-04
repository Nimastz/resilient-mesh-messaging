# services/routing_service/test/routing_config_test.py
# pytest services/routing_service/test/routing_config_test.py -v

import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from services.routing_service import routing_api
from services.routing_service import ids_module
from services.routing_service import router_db

from lib.envelope import MessageEnvelope, EnvelopeHeader, ChunkInfo, RoutingMeta
from lib.utils import current_unix_ts


client = TestClient(routing_api.app)

AUTH_HEADERS = {
    "X-Device-Fp": routing_api.DEV_DEVICE_FP,
    "X-Device-Token": routing_api.DEV_DEVICE_TOKEN,
}


def _make_env(ttl: int) -> MessageEnvelope:
    header = EnvelopeHeader(
        sender_fp="A",
        recipient_fp="B",
        msg_id="test-ttl",
        nonce="dummy",
        ttl=ttl,
        hop_count=0,
        ts=current_unix_ts(),
    )
    return MessageEnvelope(
        header=header,
        ciphertext="deadbeef",
        chunks=ChunkInfo(),
        routing=RoutingMeta(),
    )


@pytest.fixture(autouse=True)
def reset_ids_state():
    ids_module._peer_windows.clear()
    ids_module._seen_msg_ids.clear()
    ids_module._peer_suspicious_counts.clear()
    ids_module._blocked_peers.clear()
    yield


# ---------------------------------------------------------------------------
# Enqueue / TTL / duplicate / auth
# ---------------------------------------------------------------------------

def test_enqueue_rejects_ttl_below_min(monkeypatch):
    # Force config for this test
    monkeypatch.setattr(
        routing_api,
        "ROUTING_CFG",
        {"ttl_min": 2, "ttl_default": 4, "max_ttl": 8},
        raising=False,
    )
    env = _make_env(ttl=1)

    resp = client.post("/v1/router/enqueue", json=env.model_dump(), headers=AUTH_HEADERS)
    assert resp.status_code == 400
    body = resp.json()
    err = body["detail"]["error"]
    assert err["code"] == "INVALID_INPUT"


def test_enqueue_rejects_ttl_above_max(monkeypatch):
    monkeypatch.setattr(
        routing_api,
        "ROUTING_CFG",
        {"ttl_min": 1, "ttl_default": 4, "max_ttl": 3},
        raising=False,
    )
    env = _make_env(ttl=5)

    resp = client.post("/v1/router/enqueue", json=env.model_dump(), headers=AUTH_HEADERS)
    assert resp.status_code == 400
    body = resp.json()
    err = body["detail"]["error"]
    assert err["code"] == "INVALID_INPUT"


def test_enqueue_uses_default_ttl_when_none(monkeypatch):
    monkeypatch.setattr(
        routing_api,
        "ROUTING_CFG",
        {"ttl_min": 1, "ttl_default": 4, "max_ttl": 8},
        raising=False,
    )

    env = _make_env(ttl=5)
    # simulate "no ttl" after validation
    env.header.ttl = None

    resp = routing_api.api_enqueue(envelope=env, device_fp=routing_api.DEV_DEVICE_FP)
    assert resp["queued"] is True
    assert resp["msg_id"] == env.header.msg_id


def test_enqueue_duplicate_msg_id_is_dropped(monkeypatch):
    # use a reasonable config
    monkeypatch.setattr(
        routing_api,
        "ROUTING_CFG",
        {"ttl_min": 1, "ttl_default": 4, "max_ttl": 8},
        raising=False,
    )

    env = _make_env(ttl=5)  # uses fixed msg_id="test-ttl"

    # First enqueue should be queued
    resp1 = client.post("/v1/router/enqueue", json=env.model_dump(), headers=AUTH_HEADERS)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["queued"] is True

    # Second enqueue with same msg_id should be treated as duplicate and not queued
    resp2 = client.post("/v1/router/enqueue", json=env.model_dump(), headers=AUTH_HEADERS)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["queued"] is False
    assert data2["reason"] == "duplicate"


def test_enqueue_drops_too_old_message(monkeypatch):
    """
    Verify that the HTTP-layer timestamp freshness also applies to /enqueue.
    """
    monkeypatch.setattr(
        routing_api,
        "ROUTING_CFG",
        {
            "ttl_min": 1,
            "ttl_default": 4,
            "max_ttl": 8,
            "max_ts_skew_seconds": 300,
            "max_msg_age_seconds": 0,  # anything older than now is "too old"
        },
        raising=False,
    )

    env = _make_env(ttl=5)
    env.header.ts = current_unix_ts() - 10  # clearly too old

    resp = client.post("/v1/router/enqueue", json=env.model_dump(), headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["queued"] is False
    assert body["reason"] == "too_old"


def test_missing_auth_headers_returns_401():
    env = _make_env(ttl=5)
    resp = client.post("/v1/router/enqueue", json=env.model_dump())
    assert resp.status_code == 401


def test_bad_token_returns_401():
    env = _make_env(ttl=5)
    bad_headers = {
        "X-Device-Fp": routing_api.DEV_DEVICE_FP,
        "X-Device-Token": "wrong-token",
    }
    resp = client.post("/v1/router/enqueue", json=env.model_dump(), headers=bad_headers)
    assert resp.status_code == 401


def test_bad_device_fp_returns_401():
    env = _make_env(ttl=5)
    bad_headers = {
        "X-Device-Fp": "UNKNOWN-DEVICE",
        "X-Device-Token": routing_api.DEV_DEVICE_TOKEN,
    }
    resp = client.post("/v1/router/enqueue", json=env.model_dump(), headers=bad_headers)
    assert resp.status_code == 401


def test_auth_rate_limit_returns_429(monkeypatch):
    """
    If auth-level rate limiting triggers, /enqueue must return 429.
    """

    def fake_is_rate_limited(peer: str) -> bool:
        # Should be called with "auth:<ip>"
        assert peer.startswith("auth:")
        return True

    monkeypatch.setattr(routing_api, "is_rate_limited", fake_is_rate_limited, raising=False)

    env = _make_env(ttl=5)
    resp = client.post("/v1/router/enqueue", json=env.model_dump(), headers=AUTH_HEADERS)
    assert resp.status_code == 429
    body = resp.json()
    err = body["detail"]["error"]
    assert err["code"] == "UNAUTHORIZED"


# ---------------------------------------------------------------------------
# BLE ingress: timestamp freshness, TTL bounds, peer normalization
# ---------------------------------------------------------------------------

def test_on_chunk_received_action_final_by_default(monkeypatch):
    monkeypatch.setattr(
        routing_api,
        "ROUTING_CFG",
        {"forwarding_enabled": False},
        raising=False,
    )

    env = _make_env(ttl=5)
    payload = {
        "chunk": env.model_dump(),
        "link_meta": {"peer": "peer-1", "rssi": -40},
    }

    resp = client.post("/v1/router/on_chunk_received", json=payload, headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.json() == {"accepted": True, "action": "final"}


def test_on_chunk_received_action_forward_when_enabled(monkeypatch):
    monkeypatch.setattr(
        routing_api,
        "ROUTING_CFG",
        {"forwarding_enabled": True},
        raising=False,
    )

    env = _make_env(ttl=5)
    payload = {
        "chunk": env.model_dump(),
        "link_meta": {"peer": "peer-1", "rssi": -40},
    }

    resp = client.post("/v1/router/on_chunk_received", json=payload, headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.json() == {"accepted": True, "action": "forward"}


def test_on_chunk_received_rejects_future_timestamp(monkeypatch):
    # Very small skew so "now+10" looks too far in future
    monkeypatch.setattr(
        routing_api,
        "ROUTING_CFG",
        {
            "max_ts_skew_seconds": 0,
            "max_msg_age_seconds": 3600,
            "ttl_min": 1,
            "ttl_default": 4,
            "max_ttl": 8,
        },
        raising=False,
    )

    env = _make_env(ttl=5)
    env.header.ts = current_unix_ts() + 10  # clearly in future
    payload = {
        "chunk": env.model_dump(),
        "link_meta": {"peer": "peer-future", "rssi": -40},
    }

    resp = client.post("/v1/router/on_chunk_received", json=payload, headers=AUTH_HEADERS)
    assert resp.status_code == 400
    body = resp.json()
    err = body["detail"]["error"]
    assert err["code"] == "INVALID_INPUT"


def test_on_chunk_received_drops_old_message(monkeypatch):
    # Very small age so "now-10" looks too old
    monkeypatch.setattr(
        routing_api,
        "ROUTING_CFG",
        {
            "max_ts_skew_seconds": 300,
            "max_msg_age_seconds": 0,
            "ttl_min": 1,
            "ttl_default": 4,
            "max_ttl": 8,
        },
        raising=False,
    )

    env = _make_env(ttl=5)
    env.header.ts = current_unix_ts() - 10  # clearly too old
    payload = {
        "chunk": env.model_dump(),
        "link_meta": {"peer": "peer-old", "rssi": -40},
    }

    resp = client.post("/v1/router/on_chunk_received", json=payload, headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"accepted": False, "action": "drop"}


def test_on_chunk_received_rejects_ttl_above_max(monkeypatch):
    monkeypatch.setattr(
        routing_api,
        "ROUTING_CFG",
        {
            "ttl_min": 1,
            "ttl_default": 4,
            "max_ttl": 3,  # strict max
            "max_ts_skew_seconds": 300,
            "max_msg_age_seconds": 3600,
        },
        raising=False,
    )

    env = _make_env(ttl=10)  # way above max
    payload = {
        "chunk": env.model_dump(),
        "link_meta": {"peer": "peer-ttl-high", "rssi": -40},
    }

    resp = client.post("/v1/router/on_chunk_received", json=payload, headers=AUTH_HEADERS)
    assert resp.status_code == 400
    body = resp.json()
    err = body["detail"]["error"]
    assert err["code"] == "INVALID_INPUT"


def test_peer_normalization_uses_sender_fp_for_ids(monkeypatch):
    # Track which peer value is passed into is_rate_limited
    called_peers = []

    def fake_is_rate_limited(peer: str) -> bool:
        called_peers.append(peer)
        return False

    monkeypatch.setattr(routing_api, "is_rate_limited", fake_is_rate_limited, raising=False)

    env = _make_env(ttl=5)
    env.header.sender_fp = "real-sender-fp"
    payload = {
        "chunk": env.model_dump(),
        "link_meta": {"peer": "spoofed-peer", "rssi": -40},
    }

    resp = client.post("/v1/router/on_chunk_received", json=payload, headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] is True

    # Last peer passed to rate limiter must be the header sender_fp, not spoofed peer
    # (the function also gets "auth:<ip>" earlier, so grab the last call)
    assert called_peers[-1] == "real-sender-fp"


# ---------------------------------------------------------------------------
# Debug / admin endpoints & roles
# ---------------------------------------------------------------------------

def test_queue_debug_disabled_when_debug_mode_false(monkeypatch):
    monkeypatch.setattr(routing_api, "DEBUG_MODE", False, raising=False)

    resp = client.get("/v1/router/queue_debug", headers=AUTH_HEADERS)
    assert resp.status_code == 404


def test_queue_debug_enabled_when_debug_mode_true(monkeypatch):
    monkeypatch.setattr(routing_api, "DEBUG_MODE", True, raising=False)

    resp = client.get("/v1/router/queue_debug", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body


def test_stats_disabled_when_debug_mode_false(monkeypatch):
    monkeypatch.setattr(routing_api, "DEBUG_MODE", False, raising=False)

    resp = client.get("/v1/router/stats", headers=AUTH_HEADERS)
    assert resp.status_code == 404


def test_ids_log_tail_anonymizes_identifiers(monkeypatch, tmp_path):
    # use a temp log file
    log_path = tmp_path / "routing_suspicious.log"
    monkeypatch.setattr(ids_module, "LOG_PATH", log_path, raising=False)
    monkeypatch.setattr(routing_api, "IDS_LOG_PATH", log_path, raising=False)
    monkeypatch.setattr(routing_api, "DEBUG_MODE", True, raising=False)

    # write one suspicious event
    ids_module.log_suspicious("TEST_EVENT", "peer-plain", "msg-plain", "detail")

    resp = client.get("/v1/router/ids_log_tail", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    events = body["events"]
    assert len(events) >= 1
    ev = events[-1]
    # anonymized values should differ from the raw ones
    assert ev["peer"] != "peer-plain"
    assert ev["msg_id"] != "msg-plain"


# ---------------------------------------------------------------------------
# IDS behavior: block-after + auto-unblock + duplicate eviction
# ---------------------------------------------------------------------------

def test_block_peer_after_threshold(monkeypatch):
    # Reset state
    ids_module._peer_suspicious_counts.clear()
    ids_module._blocked_peers.clear()

    # Configure low threshold
    monkeypatch.setattr(ids_module, "cfg", {"block_peer_after": 3}, raising=False)

    peer = "evil-peer"

    # Log three suspicious events
    for i in range(3):
        ids_module.log_suspicious("TEST", peer, f"msg-{i}", "test event")

    # Now peer should be considered blocked by rate limiter
    assert ids_module.is_rate_limited(peer) is True


def test_blocked_peer_auto_unblocks_after_ttl(monkeypatch):
    """
    Verify BLOCK_PEER_TTL unblocks a peer after enough time:
      - Immediately after being blocked, is_rate_limited == True
      - After TTL has elapsed, is_rate_limited == False
    """
    # Make TTL small for the test
    monkeypatch.setattr(ids_module, "BLOCK_PEER_TTL", 10, raising=False)
    monkeypatch.setattr(ids_module, "cfg", {"block_peer_after": 1}, raising=False)

    base = datetime(2024, 1, 1, tzinfo=timezone.utc)

    # Phase 1: time = base for block + first rate-limit check
    def now_phase1():
        return base

    monkeypatch.setattr(ids_module, "_now", now_phase1, raising=False)

    peer = "noisy-peer"

    # Log 1 suspicious event → hits threshold, peer gets blocked at `base`
    ids_module.log_suspicious("TEST", peer, "msg-0", "detail")

    # At time `base` (< BLOCK_PEER_TTL after block), peer must still be blocked
    assert ids_module.is_rate_limited(peer) is True

    # Phase 2: advance time beyond TTL
    def now_phase2():
        # 20s > BLOCK_PEER_TTL (10s)
        return base + timedelta(seconds=20)

    monkeypatch.setattr(ids_module, "_now", now_phase2, raising=False)

    # Now peer should auto-unblock and no longer be rate-limited
    assert ids_module.is_rate_limited(peer) is False

def test_duplicate_ttl_eviction(monkeypatch):
    ids_module._seen_msg_ids.clear()
    # Remember duplicates only for 1 second
    monkeypatch.setattr(
        ids_module,
        "cfg",
        {"duplicate_suppression_ttl": 1},
        raising=False,
    )

    msg_id = "dup-test"

    assert ids_module.is_duplicate(msg_id) is False  # first time
    assert ids_module.is_duplicate(msg_id) is True   # immediate second → duplicate

    time.sleep(1.5)  # wait for TTL window to expire

    # After eviction window, it should be treated as new again
    assert ids_module.is_duplicate(msg_id) is False


# ---------------------------------------------------------------------------
# DB behavior: queue_full + dropped rows pruned from outgoing
# ---------------------------------------------------------------------------

def test_queue_full_returns_db_error(monkeypatch):
    # force max_queue_size to 0 so first insert fails
    monkeypatch.setattr(router_db, "ROUTING_CFG", {"max_queue_size": 0}, raising=False)

    env = _make_env(ttl=5)
    resp = client.post("/v1/router/enqueue", json=env.model_dump(), headers=AUTH_HEADERS)

    assert resp.status_code == 500
    body = resp.json()
    err = body["detail"]["error"]
    assert err["code"] == "DB_ERROR"


def test_mark_dropped_removes_from_outgoing(tmp_path, monkeypatch):
    """
    Ensure that rows marked dropped are no longer returned by get_outgoing().
    """
    # Use a temporary DB to avoid polluting the real one
    db_path = tmp_path / "routing.db"
    monkeypatch.setattr(router_db, "DB_PATH", str(db_path), raising=False)

    # initialize DB
    router_db.init_db()

    # Insert one queued row manually
    conn = router_db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO queue (msg_id, envelope_json, ttl, status, delivered)
        VALUES (?, ?, ?, 'queued', 0)
        """,
        ("msg-1", '{"foo": "bar"}', 4),
    )
    conn.commit()
    conn.close()

    # It should appear in outgoing
    outgoing_before = router_db.get_outgoing()
    assert len(outgoing_before) == 1
    row_id = outgoing_before[0]["row_id"]

    # Mark dropped
    router_db.mark_dropped(row_id, reason="ttl_expired")

    # Now it should *not* appear in outgoing anymore
    outgoing_after = router_db.get_outgoing()
    assert outgoing_after == []

def test_enqueue_rejects_oversized_ciphertext(monkeypatch):
    monkeypatch.setattr(
        routing_api,
        "MAX_CIPHERTEXT_BYTES",
        10,  # very small for the test
        raising=False,
    )

    env = _make_env(ttl=5)
    env.ciphertext = "A" * 100  # bigger than limit

    resp = client.post("/v1/router/enqueue", json=env.model_dump(), headers=AUTH_HEADERS)
    assert resp.status_code == 413
    body = resp.json()
    err = body["detail"]["error"]
    assert err["code"] == "INVALID_INPUT"