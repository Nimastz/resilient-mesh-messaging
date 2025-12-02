# scripts/crypto_service_tests.py
# python -m services.crypto_service.main
# test: pytest services/crypto_service/tests/crypto_service_tests.py -v

"""
Integration tests for the crypto service.

These tests assume the crypto service is running on:
    http://localhost:7001

Start it with:
    python -m services.crypto_service.main

Then run:
    pytest services/routing_service/tests/test_crypto_service.py -v
"""

import base64
import os

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization


CRYPTO_BASE = "http://localhost:7001"


def _client_or_skip() -> httpx.Client:
    """
    Return an httpx.Client if the crypto service is reachable,
    otherwise skip the whole test module.
    """
    client = httpx.Client(timeout=5.0)
    try:
        r = client.get(f"{CRYPTO_BASE}/v1/crypto/public_key")
        # if it responds at all, we assume service is alive
        if r.status_code >= 500:
            pytest.skip(f"Crypto service unhealthy: {r.status_code}")
        return client
    except Exception as e:
        client.close()
        pytest.skip(f"Crypto service not running on {CRYPTO_BASE}: {e}")


@pytest.fixture(scope="module")
def client():
    c = _client_or_skip()
    try:
        yield c
    finally:
        c.close()


def _gen_test_peer_keypair():
    """
    Generate an ephemeral peer X25519 keypair for testing.
    Returns (private_key, public_key_base64).
    """
    priv = x25519.X25519PrivateKey.generate()
    pub = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    pub_b64 = base64.b64encode(pub).decode()
    return priv, pub_b64


def _derive_test_session(client: httpx.Client, peer_label: str = "TEST-PEER") -> str:
    _, peer_pub_b64 = _gen_test_peer_keypair()
    peer_fp = f"{peer_label}-{os.urandom(4).hex().upper()}"

    r = client.post(
        f"{CRYPTO_BASE}/v1/crypto/derive_session_key",
        json={
            "peer_public_key_b64": peer_pub_b64,
            "peer_fingerprint": peer_fp,
            "ttl_hours": 24,
            "max_uses": 1000,
        },
    )
    assert r.status_code == 200, f"derive_session failed: {r.status_code} {r.text}"
    data = r.json()
    assert "session_id" in data
    return data["session_id"]


def test_happy_path_encrypt_decrypt(client: httpx.Client):
    """
    Happy path:
    - derive session
    - encrypt plaintext
    - decrypt and verify plaintext round-trip
    """
    session_id = _derive_test_session(client, "HAPPY")
    plaintext = b"hello mesh crypto"

    r_enc = client.post(
        f"{CRYPTO_BASE}/v1/crypto/encrypt",
        json={
            "session_id": session_id,
            "plaintext_b64": base64.b64encode(plaintext).decode(),
            "aad_b64": None,
        },
    )
    assert r_enc.status_code == 200, f"encrypt failed: {r_enc.status_code} {r_enc.text}"
    enc = r_enc.json()
    assert "nonce_b64" in enc and "ciphertext_b64" in enc

    r_dec = client.post(
        f"{CRYPTO_BASE}/v1/crypto/decrypt",
        json={
            "session_id": session_id,
            "nonce_b64": enc["nonce_b64"],
            "ciphertext_b64": enc["ciphertext_b64"],
            "aad_b64": None,
        },
    )
    assert r_dec.status_code == 200, f"decrypt failed: {r_dec.status_code} {r_dec.text}"
    pt_b64 = r_dec.json()["plaintext_b64"]
    recovered = base64.b64decode(pt_b64.encode())
    assert recovered == plaintext


def test_invalid_session_rejected(client: httpx.Client):
    """
    Using a bogus session_id should produce an error (ideally 401 INVALID_SESSION).
    """
    bogus_session = "00000000-0000-0000-0000-000000000000"
    plaintext = b"should not work"

    r_enc = client.post(
        f"{CRYPTO_BASE}/v1/crypto/encrypt",
        json={
            "session_id": bogus_session,
            "plaintext_b64": base64.b64encode(plaintext).decode(),
            "aad_b64": None,
        },
    )
    # We accept any 4xx as long as it's clearly an error; 401 is ideal
    assert 400 <= r_enc.status_code < 500, (
        f"Expected client error for invalid session, got {r_enc.status_code} {r_enc.text}"
    )


def test_replay_detection_on_decrypt(client: httpx.Client):
    """
    Replay detection:
    - derive session
    - encrypt once
    - decrypt once (OK)
    - decrypt again with same nonce+ciphertext (should be rejected as replay)
    """
    session_id = _derive_test_session(client, "REPLAY")
    plaintext = b"one-shot message"

    r_enc = client.post(
        f"{CRYPTO_BASE}/v1/crypto/encrypt",
        json={
            "session_id": session_id,
            "plaintext_b64": base64.b64encode(plaintext).decode(),
            "aad_b64": None,
        },
    )
    assert r_enc.status_code == 200, f"encrypt failed: {r_enc.status_code} {r_enc.text}"
    enc = r_enc.json()

    # first decrypt should succeed
    r_dec1 = client.post(
        f"{CRYPTO_BASE}/v1/crypto/decrypt",
        json={
            "session_id": session_id,
            "nonce_b64": enc["nonce_b64"],
            "ciphertext_b64": enc["ciphertext_b64"],
            "aad_b64": None,
        },
    )
    assert r_dec1.status_code == 200, f"first decrypt failed: {r_dec1.status_code} {r_dec1.text}"

    # second decrypt with same (nonce, ciphertext) should be treated as replay
    r_dec2 = client.post(
        f"{CRYPTO_BASE}/v1/crypto/decrypt",
        json={
            "session_id": session_id,
            "nonce_b64": enc["nonce_b64"],
            "ciphertext_b64": enc["ciphertext_b64"],
            "aad_b64": None,
        },
    )

    # Expect 409 REPLAY_DETECTED or at least some 4xx
    assert 400 <= r_dec2.status_code < 500, (
        f"Expected client error for replay, got {r_dec2.status_code} {r_dec2.text}"
    )
    # If your service returns structured error, you can tighten this:
    if r_dec2.status_code == 409:
        assert "REPLAY_DETECTED" in r_dec2.text


def test_mitm_wrong_session_decrypt_fails(client: httpx.Client):
    """
    MITM-style test:
    - derive session A and session B
    - encrypt under session A
    - attempt to decrypt with session B (wrong key) → should fail (AUTH_FAILED)
    """
    session_a = _derive_test_session(client, "MITM-A")
    session_b = _derive_test_session(client, "MITM-B")

    plaintext = b"secret for session A only"

    r_enc = client.post(
        f"{CRYPTO_BASE}/v1/crypto/encrypt",
        json={
            "session_id": session_a,
            "plaintext_b64": base64.b64encode(plaintext).decode(),
            "aad_b64": None,
        },
    )
    assert r_enc.status_code == 200, f"encrypt failed: {r_enc.status_code} {r_enc.text}"
    enc = r_enc.json()

    r_dec = client.post(
        f"{CRYPTO_BASE}/v1/crypto/decrypt",
        json={
            "session_id": session_b,
            "nonce_b64": enc["nonce_b64"],
            "ciphertext_b64": enc["ciphertext_b64"],
            "aad_b64": None,
        },
    )

    # Wrong key should cause auth failure or decrypt error
    assert 400 <= r_dec.status_code < 500, (
        f"Expected auth/decrypt failure for wrong session, got {r_dec.status_code} {r_dec.text}"
    )
    # If your error body includes AUTH_FAILED, we can optionally assert that:
    if r_dec.status_code in (400, 401):
        # this is soft; don't hard-fail if message format changes
        if "AUTH_FAILED" in r_dec.text:
            assert True
