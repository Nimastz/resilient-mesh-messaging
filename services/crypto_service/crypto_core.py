# services/crypto_service/crypto_core.py
# python -m services.crypto_service.main
# test: pytest services/crypto_service/tests/test_routing_stress.py -v
import base64
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional
from lib.utils import fingerprint_bytes


from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.exceptions import InvalidTag
from .keystore_db import get_connection


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------- identity key / fingerprint ----------

def load_or_create_identity() -> dict:
    """
    Ensure we have a long-term identity keypair stored in keystore.db.
    Returns {public_key_b64, fingerprint, created_at}.
    """
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT private_key, public_key, fingerprint, created_at FROM identity_key WHERE id = 1"
    ).fetchone()

    if row:
        priv_bytes, pub_bytes, fp, created_at = row
        conn.close()
        return {
            "private_key_bytes": priv_bytes,
            "public_key_b64": base64.b64encode(pub_bytes).decode(),
            "fingerprint": fp,
            "created_at": created_at,
        }

    # ---------- create new identity key ----------
    priv = x25519.X25519PrivateKey.generate()
    pub = priv.public_key()

    # For X25519, use raw encoding
    priv_bytes = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    # fingerprint = SHA-256(public_key) truncated
    fp = fingerprint_bytes(pub_bytes, out_len=16)   # 16 bytes = 128-bit fingerprint

    created_at = _now().isoformat()

    cur.execute(
        """
        INSERT INTO identity_key (id, private_key, public_key, fingerprint, created_at)
        VALUES (1, ?, ?, ?, ?)
        """,
        (priv_bytes, pub_bytes, fp, created_at),
    )
    conn.commit()
    conn.close()

    return {
        "private_key_bytes": priv_bytes,
        "public_key_b64": base64.b64encode(pub_bytes).decode(),
        "fingerprint": fp,
        "created_at": created_at,
    }


def load_identity_private_key() -> x25519.X25519PrivateKey:
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute("SELECT private_key FROM identity_key WHERE id = 1").fetchone()
    conn.close()
    if not row:
        info = load_or_create_identity()
        priv_bytes = info["private_key_bytes"]
    else:
        (priv_bytes,) = row

    return x25519.X25519PrivateKey.from_private_bytes(priv_bytes)


# ---------- ECDH sessions ----------

def create_or_update_peer(fingerprint: str, public_key_b64: str, label: str = ""):
    peer_pub = base64.b64decode(public_key_b64.encode())
    now = _now().isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO peer_key (fingerprint, public_key, label, first_seen, last_seen)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(fingerprint) DO UPDATE SET
            public_key = excluded.public_key,
            last_seen  = excluded.last_seen
        """,
        (fingerprint, peer_pub, label, now, now),
    )
    conn.commit()
    conn.close()


def derive_session(peer_fingerprint: str, peer_public_key_b64: str,
                   ttl_hours: int = 24, max_uses: int = 1000) -> dict:
    """
    Perform ECDH(identity_priv, peer_pub) and derive a symmetric session key via HKDF.
    Creates a session row in keystore.db.
    """
    identity_priv = load_identity_private_key()
    peer_pub_bytes = base64.b64decode(peer_public_key_b64.encode())
    peer_pub = x25519.X25519PublicKey.from_public_bytes(peer_pub_bytes)

    shared = identity_priv.exchange(peer_pub)

    # Derive 32 bytes via HKDF → single AES-256 key for both directions
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"mesh-session-key",
    )
    key = hkdf.derive(shared)
    send_key = key
    recv_key = key

    session_id = str(uuid.uuid4())
    created_at = _now()
    expires_at = created_at + timedelta(hours=ttl_hours)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO session (id, peer_fingerprint, send_key, recv_key,
                             created_at, expires_at, usage_count, max_uses, is_active)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?, 1)
        """,
        (
            session_id,
            peer_fingerprint,
            send_key,
            recv_key,
            created_at.isoformat(),
            expires_at.isoformat(),
            max_uses,
        ),
    )
    conn.commit()
    conn.close()

    create_or_update_peer(peer_fingerprint, peer_public_key_b64)

    return {
        "session_id": session_id,
        "peer_fingerprint": peer_fingerprint,
        "expires_at": expires_at.isoformat(),
        "max_uses": max_uses,
    }


def _load_session(session_id: str) -> Optional[dict]:
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT peer_fingerprint, send_key, recv_key, created_at, expires_at, "
        "usage_count, max_uses, is_active "
        "FROM session WHERE id = ?",
        (session_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    peer_fp, send_key, recv_key, created, expires, usage_count, max_uses, is_active = row
    return {
        "peer_fingerprint": peer_fp,
        "send_key": send_key,
        "recv_key": recv_key,
        "created_at": created,
        "expires_at": expires,
        "usage_count": usage_count,
        "max_uses": max_uses,
        "is_active": bool(is_active),
    }

# AES-GCM encrypt/decrypt with nonce & replay protection


def _check_session_active(session_row: dict) -> bool:
    if not session_row["is_active"]:
        return False
    now = _now()
    if now.isoformat() > session_row["expires_at"]:
        return False
    if session_row["usage_count"] >= session_row["max_uses"]:
        return False
    return True


def _record_nonce(session_id: str, nonce: bytes, direction: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO nonce_log (session_id, nonce, direction, used_at)
        VALUES (?, ?, ?, ?)
        """,
        (session_id, nonce, direction, _now().isoformat()),
    )
    conn.commit()
    conn.close()


def _nonce_used(session_id: str, nonce: bytes, direction: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT 1 FROM nonce_log WHERE session_id = ? AND nonce = ? AND direction = ?",
        (session_id, nonce, direction),
    ).fetchone()
    conn.close()
    return row is not None


def encrypt_with_session(session_id: str, plaintext: bytes, aad: Optional[bytes] = None) -> dict:
    row = _load_session(session_id)
    if not row or not _check_session_active(row):
        raise ValueError("INVALID_SESSION_OR_EXPIRED")

    key = row["send_key"]
    aesgcm = AESGCM(key)

    nonce = os.urandom(12)  # 96-bit GCM nonce
    if _nonce_used(session_id, nonce, "enc"):
        # extremely unlikely, but we can bail out
        raise ValueError("NONCE_REUSE_DETECTED")

    ct = aesgcm.encrypt(nonce, plaintext, aad)
    _record_nonce(session_id, nonce, "enc")

    # increment usage_count
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE session SET usage_count = usage_count + 1 WHERE id = ?",
        (session_id,),
    )
    conn.commit()
    conn.close()

    return {
        "nonce_b64": base64.b64encode(nonce).decode(),
        "ciphertext_b64": base64.b64encode(ct).decode(),
    }


def decrypt_with_session(session_id: str, nonce_b64: str, ciphertext_b64: str,
                         aad: Optional[bytes] = None) -> bytes:
    row = _load_session(session_id)
    if not row or not _check_session_active(row):
        raise ValueError("INVALID_SESSION_OR_EXPIRED")

    key = row["recv_key"]
    aesgcm = AESGCM(key)

    nonce = base64.b64decode(nonce_b64.encode())
    ct = base64.b64decode(ciphertext_b64.encode())

    # Replay protection: if we've already seen this (session, nonce, dir='dec'), treat as replay
    if _nonce_used(session_id, nonce, "dec"):
        raise ValueError("REPLAY_DETECTED")

    try:
        pt = aesgcm.decrypt(nonce, ct, aad)
    except InvalidTag:
        raise ValueError("AUTH_FAILED")

    _record_nonce(session_id, nonce, "dec")
    return pt
