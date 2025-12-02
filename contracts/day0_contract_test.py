# run:  pytest contracts/day0_contract_test.py
import json
import httpx
import jsonschema

from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "envelope_schema.json"


def load_schema():
    with SCHEMA_PATH.open("r") as f:
        return json.load(f)


def example_envelope():
    return {
        "version": "1.0",
        "header": {
            "sender_fp": "AAAABBBBCCCCDDDD1111222233334444",
            "recipient_fp": "FFFFEEEECCCCBBBB4444333322221111",
            "msg_id": "123e4567-e89b-12d3-a456-426614174000",
            "nonce": "base64nonce==",
            "ttl": 5,
            "hop_count": 0,
            "ts": 1730000000
        },
        "ciphertext": "deadbeefbase64==",
        "chunks": { "index": 0, "total": 1 },
        "routing": { "priority": "normal", "dup_suppress": True }
    }


def test_envelope_schema_valid():
    schema = load_schema()
    env = example_envelope()
    jsonschema.validate(instance=env, schema=schema)


def test_router_accepts_envelope():
    env = example_envelope()

    r = httpx.post("http://localhost:7002/v1/router/enqueue", json=env)
    assert r.status_code == 200
    assert r.json()["queued"] is True


def test_ble_accepts_chunk():
    env = example_envelope()

    r = httpx.post("http://localhost:7003/v1/ble/send_chunk",
                   json={"chunk": env, "target_peer": env["header"]["recipient_fp"]})
    assert r.status_code == 200
    assert r.json()["queued"] is True
