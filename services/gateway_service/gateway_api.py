from __future__ import annotations

import base64
from typing import Dict, Optional, List

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

from lib.envelope import MessageEnvelope
from lib.utils import build_envelope
from lib.errors import http_error, ErrorCode
from lib.auth import DEVICE_FP_HEADER, DEVICE_TOKEN_HEADER

app = FastAPI(title="Mesh Gateway API")

# ---------------------------------------------------------------------------
# Upstream service locations
# ---------------------------------------------------------------------------

CRYPTO_BASE_URL = "http://localhost:7001"
ROUTER_BASE_URL = "http://localhost:9002"
BLE_BASE_URL = "http://localhost:7003"

# Dev credentials that Gateway uses to talk to Crypto / Router.
# These must match DEV_* constants in those services.
CRYPTO_DEVICE_FP = "DEV-CRYPTO-CLIENT"
CRYPTO_DEVICE_TOKEN = "dev-crypto-token"

ROUTER_DEVICE_FP = "DEV-ROUTER-CLIENT"
ROUTER_DEVICE_TOKEN = "dev-router-token"

CRYPTO_AUTH_HEADERS = {
    DEVICE_FP_HEADER: CRYPTO_DEVICE_FP,
    DEVICE_TOKEN_HEADER: CRYPTO_DEVICE_TOKEN,
}

ROUTER_AUTH_HEADERS = {
    DEVICE_FP_HEADER: ROUTER_DEVICE_FP,
    DEVICE_TOKEN_HEADER: ROUTER_DEVICE_TOKEN,
}

# peer_fp -> session_id (in-memory)
PEER_SESSIONS: Dict[str, str] = {}

# ---------------------------------------------------------------------------
# Gateway-facing models (what your React app uses)
# ---------------------------------------------------------------------------

class DeviceRegisterRequest(BaseModel):
    """
    Web app -> Gateway -> BLE /register_device proxy.
    Mirrors DeviceRegistration in ble_api.
    """
    device_fp: str              # crypto fingerprint for this device
    platform: str               # "ios" | "android" | "desktop" | "other"
    app_version: str = "0.0.1"

    allow_auto_connect: bool = False
    allow_background_scan: bool = False
    allow_discovery: bool = False


class PairPeerRequest(BaseModel):
    """
    Called after scanning a peer's QR code.
    """
    peer_public_key_b64: str
    peer_fingerprint: str
    ttl_hours: Optional[int] = 24
    max_uses: Optional[int] = 1000


class SendMessageRequest(BaseModel):
    """
    High-level "send plaintext to peer".
    """
    peer_fp: str
    plaintext: str
    ttl: int = Field(default=4, ge=1, le=8)
    priority: str = "normal"   # must match lib.utils.validate_priority


class PollMessagesRequest(BaseModel):
    """
    Poll BLE inbox and decrypt. Web app provides device_fp + token.
    """
    device_fp: str
    device_token: str
    max_items: int = Field(default=50, ge=1, le=500)


class DecryptedMessage(BaseModel):
    msg_id: str
    from_fp: str
    plaintext: Optional[str]
    hop_count: int
    ts: int
    error: Optional[str] = None


# ---- BLE permission / scanning / nearby models ----------------------------

class PermissionUpdateRequest(BaseModel):
    """
    Web app adjusts BLE permissions (settings screen).
    Proxies to BLE /update_permissions.
    """
    device_fp: str
    device_token: str
    allow_auto_connect: Optional[bool] = None
    allow_background_scan: Optional[bool] = None
    allow_discovery: Optional[bool] = None


class PeerAuthorizeRequest(BaseModel):
    """
    Web app expresses "I allow auto-connect to this peer".
    Proxies to BLE /authorize_peer.
    """
    device_fp: str
    device_token: str
    peer_fp: str
    allow_auto_connect: bool = True


class ScanToggleRequest(BaseModel):
    """
    Web app toggles scanning for this device.
    Proxies to BLE /scan.
    """
    device_fp: str
    device_token: str
    enable: bool = True


class NearbyPeersResponse(BaseModel):
    """
    Response wrapper for /v1/gateway/peers/nearby.
    """
    peers: List[dict]


# ---------------------------------------------------------------------------
# Upstream helper functions
# ---------------------------------------------------------------------------

def _call_crypto_public_key() -> dict:
    with httpx.Client() as client:
        resp = client.get(f"{CRYPTO_BASE_URL}/v1/crypto/public_key", timeout=5.0)
    if resp.status_code != 200:
        raise http_error(
            status_code=resp.status_code,
            code=ErrorCode.INTERNAL,
            detail=f"crypto public_key upstream error: {resp.text}",
            retryable=False,
        )
    return resp.json()


def _call_crypto_derive_session(req: PairPeerRequest) -> dict:
    payload = {
        "peer_public_key_b64": req.peer_public_key_b64,
        "peer_fingerprint": req.peer_fingerprint,
        "ttl_hours": req.ttl_hours or 24,
        "max_uses": req.max_uses or 1000,
    }
    with httpx.Client() as client:
        resp = client.post(
            f"{CRYPTO_BASE_URL}/v1/crypto/derive_session_key",
            json=payload,
            headers=CRYPTO_AUTH_HEADERS,
            timeout=5.0,
        )
    if resp.status_code != 200:
        raise http_error(
            status_code=resp.status_code,
            code=ErrorCode.KEY_DERIVE_FAILED,
            detail=f"crypto derive_session upstream error: {resp.text}",
            retryable=False,
        )
    return resp.json()


def _call_crypto_encrypt(session_id: str, plaintext: str) -> dict:
    pt_b64 = base64.b64encode(plaintext.encode("utf-8")).decode("ascii")
    payload = {
        "session_id": session_id,
        "plaintext_b64": pt_b64,
        "aad_b64": None,
    }
    with httpx.Client() as client:
        resp = client.post(
            f"{CRYPTO_BASE_URL}/v1/crypto/encrypt",
            json=payload,
            headers=CRYPTO_AUTH_HEADERS,
            timeout=5.0,
        )
    if resp.status_code != 200:
        raise http_error(
            status_code=resp.status_code,
            code=ErrorCode.ENCRYPT_ERROR,
            detail=f"crypto encrypt upstream error: {resp.text}",
            retryable=False,
        )
    return resp.json()


def _call_crypto_decrypt(session_id: str, nonce_b64: str, ciphertext_b64: str) -> str:
    payload = {
        "session_id": session_id,
        "nonce_b64": nonce_b64,
        "ciphertext_b64": ciphertext_b64,
        "aad_b64": None,
    }
    with httpx.Client() as client:
        resp = client.post(
            f"{CRYPTO_BASE_URL}/v1/crypto/decrypt",
            json=payload,
            headers=CRYPTO_AUTH_HEADERS,
            timeout=5.0,
        )
    if resp.status_code != 200:
        raise http_error(
            status_code=resp.status_code,
            code=ErrorCode.DECRYPT_ERROR,
            detail=f"crypto decrypt upstream error: {resp.text}",
            retryable=False,
        )
    data = resp.json()
    pt_b64 = data["plaintext_b64"]
    return base64.b64decode(pt_b64.encode("ascii")).decode("utf-8")


def _call_router_enqueue(env: MessageEnvelope) -> dict:
    with httpx.Client() as client:
        resp = client.post(
            f"{ROUTER_BASE_URL}/v1/router/enqueue",
            json=env.model_dump(),
            headers=ROUTER_AUTH_HEADERS,
            timeout=5.0,
        )
    if resp.status_code != 200:
        raise http_error(
            status_code=resp.status_code,
            code=ErrorCode.INTERNAL,
            detail=f"router enqueue upstream error: {resp.text}",
            retryable=False,
        )
    return resp.json()


def _call_ble_register_device(req: DeviceRegisterRequest) -> dict:
    with httpx.Client() as client:
        resp = client.post(
            f"{BLE_BASE_URL}/v1/ble/register_device",
            json=req.model_dump(),
            timeout=5.0,
        )
    if resp.status_code != 200:
        raise http_error(
            status_code=resp.status_code,
            code=ErrorCode.INTERNAL,
            detail=f"BLE register_device upstream error: {resp.text}",
            retryable=False,
        )
    return resp.json()


def _ble_headers(device_fp: str, device_token: str) -> dict:
    return {
        DEVICE_FP_HEADER: device_fp,
        DEVICE_TOKEN_HEADER: device_token,
    }


def _call_ble_poll_inbox(req: PollMessagesRequest) -> List[dict]:
    body = {
        "device_fp": req.device_fp,
        "max_items": req.max_items,
    }
    headers = _ble_headers(req.device_fp, req.device_token)
    with httpx.Client() as client:
        resp = client.post(
            f"{BLE_BASE_URL}/v1/ble/poll_inbox",
            json=body,
            headers=headers,
            timeout=5.0,
        )
    if resp.status_code != 200:
        raise http_error(
            status_code=resp.status_code,
            code=ErrorCode.INTERNAL,
            detail=f"BLE poll_inbox upstream error: {resp.text}",
            retryable=False,
        )
    data = resp.json()
    return data.get("chunks", [])


def _call_ble_update_permissions(req: PermissionUpdateRequest) -> dict:
    body = {
        "device_fp": req.device_fp,
        "allow_auto_connect": req.allow_auto_connect,
        "allow_background_scan": req.allow_background_scan,
        "allow_discovery": req.allow_discovery,
    }
    headers = _ble_headers(req.device_fp, req.device_token)
    with httpx.Client() as client:
        resp = client.post(
            f"{BLE_BASE_URL}/v1/ble/update_permissions",
            json=body,
            headers=headers,
            timeout=5.0,
        )
    if resp.status_code != 200:
        raise http_error(
            status_code=resp.status_code,
            code=ErrorCode.INTERNAL,
            detail=f"BLE update_permissions upstream error: {resp.text}",
            retryable=False,
        )
    return resp.json()


def _call_ble_authorize_peer(req: PeerAuthorizeRequest) -> dict:
    body = {
        "device_fp": req.device_fp,
        "peer_fp": req.peer_fp,
        "allow_auto_connect": req.allow_auto_connect,
    }
    headers = _ble_headers(req.device_fp, req.device_token)
    with httpx.Client() as client:
        resp = client.post(
            f"{BLE_BASE_URL}/v1/ble/authorize_peer",
            json=body,
            headers=headers,
            timeout=5.0,
        )
    if resp.status_code != 200:
        raise http_error(
            status_code=resp.status_code,
            code=ErrorCode.INTERNAL,
            detail=f"BLE authorize_peer upstream error: {resp.text}",
            retryable=False,
        )
    return resp.json()


def _call_ble_set_scan(req: ScanToggleRequest) -> dict:
    body = {
        "device_fp": req.device_fp,
        "enable": req.enable,
    }
    headers = _ble_headers(req.device_fp, req.device_token)
    with httpx.Client() as client:
        resp = client.post(
            f"{BLE_BASE_URL}/v1/ble/scan",
            json=body,
            headers=headers,
            timeout=5.0,
        )
    if resp.status_code != 200:
        raise http_error(
            status_code=resp.status_code,
            code=ErrorCode.INTERNAL,
            detail=f"BLE scan upstream error: {resp.text}",
            retryable=False,
        )
    return resp.json()


def _call_ble_nearby_peers(device_fp: str, device_token: str) -> dict:
    headers = _ble_headers(device_fp, device_token)
    params = {"device_fp": device_fp}
    with httpx.Client() as client:
        resp = client.get(
            f"{BLE_BASE_URL}/v1/ble/peers/nearby",
            params=params,
            headers=headers,
            timeout=5.0,
        )
    if resp.status_code != 200:
        raise http_error(
            status_code=resp.status_code,
            code=ErrorCode.INTERNAL,
            detail=f"BLE peers/nearby upstream error: {resp.text}",
            retryable=False,
        )
    return resp.json()


# ---------------------------------------------------------------------------
# Public Gateway endpoints
# ---------------------------------------------------------------------------

@app.get("/healthz")
def healthcheck():
    return {"status": "ok"}


@app.get("/v1/gateway/identity")
def get_identity():
    """
    Identity for QR display: curve, public_key_b64, fingerprint.
    """
    return _call_crypto_public_key()


@app.post("/v1/gateway/device/register")
def register_device(req: DeviceRegisterRequest):
    """
    Register this device with BLE adapter and obtain device API token.
    """
    return _call_ble_register_device(req)


@app.post("/v1/gateway/pair_peer")
def pair_peer(req: PairPeerRequest):
    """
    After scanning peer QR: derive session + remember session_id for peer_fp.
    """
    session_info = _call_crypto_derive_session(req)
    session_id = session_info["session_id"]
    peer_fp = session_info["peer_fingerprint"]

    PEER_SESSIONS[peer_fp] = session_id

    return {
        "session_id": session_id,
        "peer_fingerprint": peer_fp,
        "expires_at": session_info["expires_at"],
        "max_uses": session_info["max_uses"],
    }


@app.post("/v1/gateway/send_message")
def send_message(req: SendMessageRequest):
    """
    Send plaintext to peer:
      - lookup session
      - encrypt via Crypto
      - build MessageEnvelope
      - enqueue in Router
    """
    session_id = PEER_SESSIONS.get(req.peer_fp)
    if not session_id:
        raise http_error(
            status_code=400,
            code=ErrorCode.INVALID_INPUT,
            detail="No session for this peer_fp; call /pair_peer first.",
            retryable=False,
        )

    identity = _call_crypto_public_key()
    sender_fp = identity["fingerprint"]

    enc = _call_crypto_encrypt(session_id=session_id, plaintext=req.plaintext)
    nonce_b64 = enc["nonce_b64"]
    ciphertext_b64 = enc["ciphertext_b64"]

    envelope = build_envelope(
        sender_fp=sender_fp,
        recipient_fp=req.peer_fp,
        ciphertext_b64=ciphertext_b64,
        ttl=req.ttl,
        priority=req.priority,
        nonce_b64=nonce_b64,
    )

    enqueue_result = _call_router_enqueue(envelope)

    return {
        "queued": enqueue_result.get("queued", False),
        "msg_id": envelope.header.msg_id,
        "router_result": enqueue_result,
    }


@app.post("/v1/gateway/poll_messages")
def poll_messages(req: PollMessagesRequest):
    """
    Poll BLE inbox, decrypt messages where we have a session, and return
    plaintext list to the web client.
    """
    chunks = _call_ble_poll_inbox(req)
    messages: List[DecryptedMessage] = []

    for raw in chunks:
        env = MessageEnvelope.model_validate(raw)
        sender_fp = env.header.sender_fp
        msg_id = env.header.msg_id

        session_id = PEER_SESSIONS.get(sender_fp)
        if not session_id:
            messages.append(
                DecryptedMessage(
                    msg_id=msg_id,
                    from_fp=sender_fp,
                    plaintext=None,
                    hop_count=env.header.hop_count,
                    ts=env.header.ts,
                    error="no_session_for_sender",
                )
            )
            continue

        try:
            plaintext = _call_crypto_decrypt(
                session_id=session_id,
                nonce_b64=env.header.nonce,
                ciphertext_b64=env.ciphertext,
            )
            messages.append(
                DecryptedMessage(
                    msg_id=msg_id,
                    from_fp=sender_fp,
                    plaintext=plaintext,
                    hop_count=env.header.hop_count,
                    ts=env.header.ts,
                )
            )
        except Exception as exc:
            messages.append(
                DecryptedMessage(
                    msg_id=msg_id,
                    from_fp=sender_fp,
                    plaintext=None,
                    hop_count=env.header.hop_count,
                    ts=env.header.ts,
                    error=f"decrypt_failed: {exc}",
                )
            )

    return {"messages": [m.model_dump() for m in messages]}


# ---------------------------------------------------------------------------
# BLE permission & discovery endpoints (for your app settings UI)
# ---------------------------------------------------------------------------

@app.post("/v1/gateway/permissions/update")
def update_permissions(req: PermissionUpdateRequest):
    """
    Update BLE permissions for this device.
    This keeps BLE's rule: a device can only modify its own permissions.
    """
    return _call_ble_update_permissions(req)


@app.post("/v1/gateway/peer/authorize")
def authorize_peer(req: PeerAuthorizeRequest):
    """
    Express "I allow auto-connect to this peer" (or revoke).
    """
    return _call_ble_authorize_peer(req)


@app.post("/v1/gateway/scan")
def set_scan(req: ScanToggleRequest):
    """
    Toggle scanning state for this device.
    """
    return _call_ble_set_scan(req)


@app.get("/v1/gateway/peers/nearby", response_model=NearbyPeersResponse)
def nearby_peers(device_fp: str, device_token: str):
    """
    List nearby discoverable peers according to BLE adapter rules.
    """
    data = _call_ble_nearby_peers(device_fp=device_fp, device_token=device_token)
    return data
