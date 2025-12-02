# services/crypto_service/api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from .keystore_db import init_keystore_db
from .crypto_core import (
    load_or_create_identity,
    derive_session,
    encrypt_with_session,
    decrypt_with_session,
)

app = FastAPI()


@app.on_event("startup")
def startup():
    init_keystore_db()
    load_or_create_identity()


def error_response(code: str, detail: str, status: int = 400, retryable: bool = False):
    raise HTTPException(
        status_code=status,
        detail={"error": {"code": code, "detail": detail, "retryable": retryable}},
    )


# ---------- Schemas ----------

class DeriveSessionRequest(BaseModel):
    peer_public_key_b64: str
    peer_fingerprint: str
    ttl_hours: Optional[int] = 24
    max_uses: Optional[int] = 1000


class EncryptRequest(BaseModel):
    session_id: str
    plaintext_b64: str
    aad_b64: Optional[str] = None


class DecryptRequest(BaseModel):
    session_id: str
    nonce_b64: str
    ciphertext_b64: str
    aad_b64: Optional[str] = None


# ---------- Endpoints ----------

@app.get("/v1/crypto/public_key")
def get_public_key():
    info = load_or_create_identity()
    return {
        "curve": "X25519",
        "public_key": info["public_key_b64"],
        "fingerprint": info["fingerprint"],
        "created_at": info["created_at"],
    }


@app.post("/v1/crypto/derive_session_key")
def api_derive_session(req: DeriveSessionRequest):
    try:
        session_info = derive_session(
            peer_fingerprint=req.peer_fingerprint,
            peer_public_key_b64=req.peer_public_key_b64,
            ttl_hours=req.ttl_hours or 24,
            max_uses=req.max_uses or 1000,
        )
        return {
            "session_id": session_info["session_id"],
            "peer_fingerprint": session_info["peer_fingerprint"],
            "expires_at": session_info["expires_at"],
            "max_uses": session_info["max_uses"],
        }
    except Exception as e:
        error_response("KEY_DERIVE_FAILED", f"Failed to derive session key: {e}", status=500)


@app.post("/v1/crypto/encrypt")
def api_encrypt(req: EncryptRequest):
    import base64
    try:
        plaintext = base64.b64decode(req.plaintext_b64.encode())
        aad = base64.b64decode(req.aad_b64.encode()) if req.aad_b64 else None

        result = encrypt_with_session(req.session_id, plaintext, aad)
        return result
    except ValueError as ve:
        code = str(ve)
        if "INVALID_SESSION" in code:
            error_response("INVALID_SESSION", "Session invalid or expired", status=401)
        if "NONCE_REUSE" in code:
            error_response("NONCE_REUSE", "Nonce reuse detected", status=409)
        error_response("ENCRYPT_ERROR", f"{ve}", status=400)
    except Exception as e:
        error_response("INTERNAL", f"Internal crypto error: {e}", status=500)


@app.post("/v1/crypto/decrypt")
def api_decrypt(req: DecryptRequest):
    import base64
    try:
        aad = base64.b64decode(req.aad_b64.encode()) if req.aad_b64 else None
        plaintext = decrypt_with_session(
            req.session_id,
            req.nonce_b64,
            req.ciphertext_b64,
            aad,
        )
        return {
            "plaintext_b64": base64.b64encode(plaintext).decode()
        }
    except ValueError as ve:
        msg = str(ve)
        if "INVALID_SESSION" in msg:
            error_response("INVALID_SESSION", "Session invalid or expired", status=401)
        if "REPLAY_DETECTED" in msg:
            error_response("REPLAY_DETECTED", "Replay detected", status=409, retryable=False)
        if "AUTH_FAILED" in msg:
            error_response("AUTH_FAILED", "GCM tag verification failed", status=401)
        error_response("DECRYPT_ERROR", msg, status=400)
    except Exception as e:
        error_response("INTERNAL", f"Internal crypto error: {e}", status=500)
