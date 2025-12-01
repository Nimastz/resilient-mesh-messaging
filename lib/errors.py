# lib/errors.py
"""
Shared error helpers for all services.

- Enforces the common error body:
    {"error": {"code": "...", "detail": "...", "retryable": false}}
- Central place for error codes so we don't diverge between services.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

try:
    # FastAPI is only available inside service processes – this import
    # is optional so utils can still be used in plain scripts/tests.
    from fastapi import HTTPException  # type: ignore
except Exception:  # pragma: no cover - used only when FastAPI present
    HTTPException = None  # type: ignore


class ErrorCode(str, Enum):
    # Day-0 shared codes (from integration contract)
    INVALID_INPUT = "INVALID_INPUT"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    REPLAY_DETECTED = "REPLAY_DETECTED"
    NONCE_REUSE = "NONCE_REUSE"
    DB_ERROR = "DB_ERROR"
    BLE_UNAVAILABLE = "BLE_UNAVAILABLE"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL = "INTERNAL"

    # Crypto / session specific
    INVALID_SESSION = "INVALID_SESSION"
    AUTH_FAILED = "AUTH_FAILED"

    # Routing / TTL specific
    TTL_EXPIRED = "TTL_EXPIRED"


@dataclass
class ErrorPayload:
    """
    Represents the standard error body.

    Example JSON:
        {
          "error": {
            "code": "INVALID_INPUT",
            "detail": "msg_id missing",
            "retryable": false
          }
        }
    """
    code: str
    detail: str
    retryable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "detail": self.detail,
                "retryable": self.retryable,
            }
        }


def make_error(
    code: ErrorCode | str,
    detail: str,
    retryable: bool = False,
) -> Dict[str, Any]:
    """
    Build the shared error JSON body (no HTTP semantics).
    """
    payload = ErrorPayload(code=str(code), detail=detail, retryable=retryable)
    return payload.to_dict()


def http_error(
    status_code: int,
    code: ErrorCode | str,
    detail: str,
    retryable: bool = False,
) -> Exception:
    """
    Convenience helper for FastAPI routes.

    Usage:
        from lib.errors import http_error, ErrorCode

        if bad_input:
            raise http_error(400, ErrorCode.INVALID_INPUT, "msg_id required")
    """
    if HTTPException is None:  # pragma: no cover
        # Fallback so this can still be used in non-FastAPI contexts
        return RuntimeError(f"{status_code} {code}: {detail}")

    return HTTPException(
        status_code=status_code,
        detail=make_error(code, detail, retryable),
    )
