# services/tests/routing_stress_tests.py
import asyncio
import httpx
import uuid
import time
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.envelope import MessageEnvelope, EnvelopeHeader, ChunkInfo, RoutingMeta

ROUTER_BASE = "http://localhost:9002"   # or 7002 if you change the port


def make_envelope(sender_fp: str, recipient_fp: str, ttl: int = 5) -> MessageEnvelope:
    msg_id = str(uuid.uuid4())
    header = EnvelopeHeader(
        sender_fp=sender_fp,
        recipient_fp=recipient_fp,
        msg_id=msg_id,
        nonce="dummy-nonce",
        ttl=ttl,
        hop_count=0,
        ts=int(time.time()),
    )
    return MessageEnvelope(
        header=header,
        ciphertext="deadbeef",    # placeholder
        chunks=ChunkInfo(),
        routing=RoutingMeta(),
    )


async def simulate_message_storm(peer: str, count: int = 100):
    async with httpx.AsyncClient() as client:
        for _ in range(count):
            env = make_envelope(sender_fp=peer, recipient_fp="target")
            payload = {
                "chunk": env.dict(),
                "link_meta": {"peer": peer, "rssi": -40},
            }
            resp = await client.post(f"{ROUTER_BASE}/v1/router/on_chunk_received", json=payload)
            print("storm:", resp.status_code, resp.json())


async def simulate_node_churn(peers: list[str], messages_per_peer: int = 5):
    async with httpx.AsyncClient() as client:
        for peer in peers:
            for _ in range(messages_per_peer):
                env = make_envelope(sender_fp=peer, recipient_fp="target")
                payload = {
                    "chunk": env.dict(),
                    "link_meta": {"peer": peer, "rssi": -60},
                }
                resp = await client.post(f"{ROUTER_BASE}/v1/router/on_chunk_received", json=payload)
                print("churn:", peer, resp.status_code, resp.json())


async def simulate_partitions():
    """
    Very rough: we just send messages with small TTL to simulate them dying
    before reaching destination.
    """
    async with httpx.AsyncClient() as client:
        for _ in range(10):
            env = make_envelope(sender_fp="peer-partitioned", recipient_fp="far-away", ttl=0)
            payload = {
                "chunk": env.dict(),
                "link_meta": {"peer": "peer-partitioned", "rssi": -90},
            }
            resp = await client.post(f"{ROUTER_BASE}/v1/router/on_chunk_received", json=payload)
            print("partition:", resp.status_code, resp.json())


async def main():
    print("== Storm test ==")
    await simulate_message_storm("stormy-peer", 40)

    print("== Node churn ==")
    await simulate_node_churn([f"peer-{i}" for i in range(5)], messages_per_peer=3)

    print("== Partition ==")
    await simulate_partitions()


if __name__ == "__main__":
    asyncio.run(main())
