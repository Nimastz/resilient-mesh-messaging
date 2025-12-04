# services/routing_service/test/routing_test.py
# pytest services/routing_service/test/routing_ids.py -v
import time
import uuid
import httpx
import pytest

from lib.envelope import MessageEnvelope, EnvelopeHeader, ChunkInfo, RoutingMeta


ROUTER_BASE = "http://localhost:9002"  # adjust if you change the port

# Must match DEV_DEVICE_FP / DEV_DEVICE_TOKEN in routing_api
DEVICE_FP = "DEV-ROUTER-CLIENT"
DEVICE_TOKEN = "dev-router-token"

AUTH_HEADERS = {
    "X-Device-Fp": DEVICE_FP,
    "X-Device-Token": DEVICE_TOKEN,
}


def _now_ts() -> int:
    return int(time.time())


def make_envelope(sender_fp: str, recipient_fp: str, ttl: int = 5) -> MessageEnvelope:
    msg_id = str(uuid.uuid4())
    header = EnvelopeHeader(
        sender_fp=sender_fp,
        recipient_fp=recipient_fp,
        msg_id=msg_id,
        nonce="dummy-nonce",
        ttl=ttl,
        hop_count=0,
        ts=_now_ts(),
    )
    return MessageEnvelope(
        header=header,
        ciphertext="deadbeef",  # placeholder AES-GCM ciphertext
        chunks=ChunkInfo(),
        routing=RoutingMeta(),
    )


async def _ensure_router_or_skip():
    """
    Try hitting /v1/router/stats; if it fails, skip tests.
    """
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            r = await client.get(
                f"{ROUTER_BASE}/v1/router/stats",
                headers=AUTH_HEADERS,
            )
        except Exception as e:
            pytest.skip(f"Router service not running on {ROUTER_BASE}: {e}")

        if r.status_code >= 500:
            pytest.skip(f"Router service unhealthy: {r.status_code} {r.text}")


@pytest.mark.anyio
async def test_message_storm_triggers_rate_limit():
    """
    Send a burst of messages from a single peer.

    Expected behavior with your IDS:
    - some messages are accepted
    - later ones are dropped due to per-peer rate limiting
    """
    await _ensure_router_or_skip()

    peer = "stormy-peer"
    total = 40
    accepted = 0
    dropped = 0

    async with httpx.AsyncClient(timeout=5.0) as client:
        for _ in range(total):
            env = make_envelope(sender_fp=peer, recipient_fp="target")
            payload = {
                "chunk": env.model_dump(),
                "link_meta": {"peer": peer, "rssi": -40},
            }
            r = await client.post(
                f"{ROUTER_BASE}/v1/router/on_chunk_received",
                headers=AUTH_HEADERS,
                json=payload,
            )
            assert r.status_code == 200, f"Unexpected status: {r.status_code} {r.text}"
            body = r.json()
            if body.get("accepted"):
                accepted += 1
            else:
                dropped += 1

    # We expect some accepted, some dropped (IDS engaged)
    assert accepted > 0, "Storm test: no messages were accepted"
    assert dropped > 0, "Storm test: no messages were dropped; IDS rate limit may not be working"


@pytest.mark.anyio
async def test_node_churn_multiple_peers_ok():
    """
    Simulate 'node churn' – several peers each sending a few messages.

    Expected behavior:
    - messages from different peers within limits should generally be accepted
    """
    await _ensure_router_or_skip()

    peers = [f"peer-{i}" for i in range(5)]
    messages_per_peer = 3
    total = len(peers) * messages_per_peer

    accepted = 0
    dropped = 0

    async with httpx.AsyncClient(timeout=5.0) as client:
        for peer in peers:
            for _ in range(messages_per_peer):
                env = make_envelope(sender_fp=peer, recipient_fp="target")
                payload = {
                    "chunk": env.model_dump(),
                    "link_meta": {"peer": peer, "rssi": -60},
                }
                r = await client.post(
                    f"{ROUTER_BASE}/v1/router/on_chunk_received",
                    headers=AUTH_HEADERS,
                    json=payload,
                )
                assert r.status_code == 200, f"Node churn: {peer} got {r.status_code} {r.text}"
                body = r.json()
                if body.get("accepted"):
                    accepted += 1
                else:
                    dropped += 1

    # In this mild churn case, we expect no or very few drops
    assert accepted > 0, "Node churn: no messages were accepted"
    # it's okay if dropped > 0, but if ALL dropped, something is wrong:
    assert accepted >= total / 2, "Too many messages dropped under light node churn"


@pytest.mark.anyio
async def test_partition_ttl_expired():
    """
    Simulate 'network partition' by sending messages with ttl=0.

    Expected behavior:
    - router should reply with HTTP 410 and error code TTL_EXPIRED.
    """
    await _ensure_router_or_skip()

    attempts = 5
    async with httpx.AsyncClient(timeout=5.0) as client:
        for _ in range(attempts):
            env = make_envelope(
                sender_fp="peer-partitioned",
                recipient_fp="far-away",
                ttl=0,
            )
            payload = {
                "chunk": env.model_dump(),
                "link_meta": {"peer": "peer-partitioned", "rssi": -90},
            }
            r = await client.post(
                f"{ROUTER_BASE}/v1/router/on_chunk_received",
                headers=AUTH_HEADERS,
                json=payload,
            )
            assert r.status_code == 410, (
                f"Expected 410 TTL_EXPIRED, got {r.status_code} {r.text}"
            )
            body = r.json()
            # if you use standard error format, we can check code:
            if isinstance(body, dict) and "detail" in body:
                err = body["detail"].get("error", {})
                assert err.get("code") == "TTL_EXPIRED"
