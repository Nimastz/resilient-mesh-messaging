# services/crypto_service/api.py

from fastapi import FastAPI
from pydantic import BaseModel

from crypto_service.crypto_core import (
    load_or_create_identity,
    derive_session,
    encrypt_with_session,
    decrypt_with_session,
)
from lib.utils import b64decode
from lib.errors import http_error, ErrorCode


app = FastAPI()

class DeriveSessionRequest(BaseModel):
    peer_public_key_b64: str
    peer_fingerprint: str
    ttl_hours: int = 24
    max_uses: int = 1000


class EncryptRequest(BaseModel):
    session_id: str
    plaintext_b64: str
    aad_b64: str | None = None


class DecryptRequest(BaseModel):
    session_id: str
    nonce_b64: str
    ciphertext_b64: str
    aad_b64: str | None = None


@app.get("/v1/crypto/public_key")
def get_public_key():
    """
    Return identity public key + fingerprint for QR / out-of-band exchange.
    """
    info = load_or_create_identity()
    return {
        "public_key_b64": info["public_key_b64"],
        "fingerprint": info["fingerprint"],
        "created_at": info["created_at"],
    }


@app.post("/v1/crypto/derive_session_key")
def api_derive_session_key(req: DeriveSessionRequest):
    """
    ECDH + HKDF to create a new session row in keystore.db.

    Request from tests:
      {
        "peer_public_key_b64": "...",
        "peer_fingerprint": "HAPPY-ABCD...",
        "ttl_hours": 24,
        "max_uses": 1000
      }
    """
    try:
        result = derive_session(
            peer_fingerprint=req.peer_fingerprint,
            peer_public_key_b64=req.peer_public_key_b64,
            ttl_hours=req.ttl_hours,
            max_uses=req.max_uses,
        )
        # result already contains {session_id, peer_fingerprint, expires_at, max_uses}
        return result
    except Exception as e:
        # internal error – should be rare
        raise http_error(
            status_code=500,
            code=ErrorCode.INTERNAL,
            detail=f"derive_session_key failed: {e}",
        )


@app.post("/v1/crypto/encrypt")
def api_encrypt(req: EncryptRequest):
    """
    Encrypt plaintext under a given session.
    """
    try:
        plaintext = b64decode(req.plaintext_b64)
        aad = b64decode(req.aad_b64) if req.aad_b64 else None
        out = encrypt_with_session(req.session_id, plaintext, aad)
        return out
    except ValueError as e:
        msg = str(e)
        if msg == "INVALID_SESSION_OR_EXPIRED":
            raise http_error(401, ErrorCode.INVALID_SESSION, msg)
        if msg == "NONCE_REUSE_DETECTED":
            raise http_error(409, ErrorCode.NONCE_REUSE, msg, retryable=True)
        raise http_error(400, ErrorCode.INVALID_INPUT, msg)
    except Exception as e:
        raise http_error(500, ErrorCode.INTERNAL, f"encrypt failed: {e}")


@app.post("/v1/crypto/decrypt")
def api_decrypt(req: DecryptRequest):
    """
    Decrypt ciphertext under a given session with replay protection.
    """
    try:
        aad = b64decode(req.aad_b64) if req.aad_b64 else None
        pt = decrypt_with_session(
            req.session_id,
            req.nonce_b64,
            req.ciphertext_b64,
            aad,
        )
        from lib.utils import b64encode
        return {"plaintext_b64": b64encode(pt)}
    except ValueError as e:
        msg = str(e)
        if msg == "INVALID_SESSION_OR_EXPIRED":
            raise http_error(401, ErrorCode.INVALID_SESSION, msg)
        if msg == "REPLAY_DETECTED":
            raise http_error(409, ErrorCode.REPLAY_DETECTED, msg, retryable=False)
        if msg == "AUTH_FAILED":
            raise http_error(401, ErrorCode.AUTH_FAILED, msg)
        raise http_error(400, ErrorCode.INVALID_INPUT, msg)
    except Exception as e:
        raise http_error(500, ErrorCode.INTERNAL, f"decrypt failed: {e}")
