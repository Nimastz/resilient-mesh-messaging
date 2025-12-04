# services/routing_service/test/routing_config_test.py
# test: pytest services/routing_service/test/routing_config_test.py -v

from fastapi.testclient import TestClient
import pytest
from services.routing_service import routing_api
from lib.envelope import MessageEnvelope, EnvelopeHeader, ChunkInfo, RoutingMeta
from lib.utils import current_unix_ts
from services.routing_service import ids_module
import time

client = TestClient(routing_api.app)
AUTH_HEADERS = {
    "X-Device-Fp": routing_api.DEV_DEVICE_FP,
    "X-Device-Token": routing_api.DEV_DEVICE_TOKEN,
}

def _make_env(ttl):
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
    
def test_enqueue_rejects_ttl_below_min(monkeypatch):
    # Force config for this test
    monkeypatch.setattr(routing_api, "ROUTING_CFG", {"ttl_min": 2, "ttl_default": 4, "max_ttl": 8})
    env = _make_env(ttl=1)

    resp = client.post("/v1/router/enqueue", json=env.model_dump(), headers=AUTH_HEADERS)
    assert resp.status_code == 400
    body = resp.json()
    err = body["detail"]["error"]
    assert err["code"] == "INVALID_INPUT"

def test_enqueue_rejects_ttl_above_max(monkeypatch):
    monkeypatch.setattr(routing_api, "ROUTING_CFG", {"ttl_min": 1, "ttl_default": 4, "max_ttl": 3})
    env = _make_env(ttl=5)

    resp = client.post("/v1/router/enqueue", json=env.model_dump(), headers=AUTH_HEADERS)
    assert resp.status_code == 400
    body = resp.json()
    err = body["detail"]["error"]
    assert err["code"] == "INVALID_INPUT"


def test_enqueue_uses_default_ttl_when_none(monkeypatch):
    monkeypatch.setattr(routing_api, "ROUTING_CFG", {"ttl_min": 1, "ttl_default": 4, "max_ttl": 8})

    env = _make_env(ttl=5)
    # simulate "no ttl" after validation
    env.header.ttl = None

    resp = routing_api.api_enqueue(envelope=env, device_fp=routing_api.DEV_DEVICE_FP)
    assert resp["queued"] is True
    assert resp["msg_id"] == env.header.msg_id



def test_on_chunk_received_action_final_by_default(monkeypatch):
    monkeypatch.setattr(routing_api, "ROUTING_CFG", {"forwarding_enabled": False})

    env = _make_env(ttl=5)
    payload = {
        "chunk": env.model_dump(),
        "link_meta": {"peer": "peer-1", "rssi": -40},
    }

    resp = client.post("/v1/router/on_chunk_received", json=payload, headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.json() == {"accepted": True, "action": "final"}

def test_on_chunk_received_action_forward_when_enabled(monkeypatch):
    monkeypatch.setattr(routing_api, "ROUTING_CFG", {"forwarding_enabled": True})

    env = _make_env(ttl=5)
    payload = {
        "chunk": env.model_dump(),
        "link_meta": {"peer": "peer-1", "rssi": -40},
    }

    resp = client.post("/v1/router/on_chunk_received", json=payload, headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.json() == {"accepted": True, "action": "forward"}


def test_block_peer_after_threshold(monkeypatch):
    # Reset state
    ids_module._peer_suspicious_counts.clear()
    ids_module._blocked_peers.clear()

    # Set low threshold for test
    monkeypatch.setattr(ids_module, "cfg", {"block_peer_after": 3, "window_seconds": 5, "max_msgs_per_window": 100})

    peer = "evil-peer"

    # Log three suspicious events
    for i in range(3):
        ids_module.log_suspicious("TEST", peer, f"msg-{i}", "test event")

    # Now peer should be considered blocked by rate limiter
    assert ids_module.is_rate_limited(peer) is True


def test_duplicate_ttl_eviction(monkeypatch):
    ids_module._seen_msg_ids.clear()
    # Remember duplicates only for 1 second
    monkeypatch.setattr(ids_module, "cfg", {"duplicate_suppression_ttl": 1, "window_seconds": 5, "max_msgs_per_window": 100})

    msg_id = "dup-test"

    assert ids_module.is_duplicate(msg_id) is False  # first time
    assert ids_module.is_duplicate(msg_id) is True   # immediate second → duplicate

    time.sleep(1.5)  # wait for TTL window to expire

    # After eviction window, it should be treated as new again
    assert ids_module.is_duplicate(msg_id) is False

def test_queue_full_returns_db_error(monkeypatch):
    # force max_queue_size to 0 so first insert fails
    from services.routing_service import router_db

    monkeypatch.setattr(router_db, "ROUTING_CFG", {"max_queue_size": 0})

    env = _make_env(ttl=5)
    resp = client.post("/v1/router/enqueue", json=env.model_dump(), headers=AUTH_HEADERS)

    assert resp.status_code == 500
    body = resp.json()
    err = body["detail"]["error"]
    assert err["code"] == "DB_ERROR"

