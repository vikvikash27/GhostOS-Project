
"""Validation and response helpers for the GhostCore IPC protocol."""

from __future__ import annotations

import json
from typing import Any

PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 65_536


class ProtocolError(ValueError):
    """Raised when an IPC message is invalid."""


def encode_message(message: dict[str, Any]) -> bytes:
    """Encode one JSON message terminated by a newline."""
    try:
        encoded = json.dumps(
            message,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8") + b"\n"
    except (TypeError, ValueError) as exc:
        raise ProtocolError("Message cannot be encoded") from exc

    if len(encoded) > MAX_MESSAGE_BYTES:
        raise ProtocolError("Message exceeds the size limit")

    return encoded


def decode_request(raw: bytes) -> dict[str, Any]:
    """Decode and validate a single IPC request."""
    if not raw or len(raw) > MAX_MESSAGE_BYTES:
        raise ProtocolError("Invalid message size")

    if not raw.endswith(b"\n"):
        raise ProtocolError("Message must end with a newline")

    try:
        request = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("Invalid JSON") from exc

    if not isinstance(request, dict):
        raise ProtocolError("Request must be a JSON object")

    if set(request) != {"version", "id", "operation", "params"}:
        raise ProtocolError("Unexpected or missing request fields")

    if request["version"] != PROTOCOL_VERSION:
        raise ProtocolError("Unsupported protocol version")

    request_id = request["id"]
    if (
        not isinstance(request_id, str)
        or not request_id
        or len(request_id) > 64
    ):
        raise ProtocolError("Invalid request ID")

    operation = request["operation"]
    if not isinstance(operation, str) or len(operation) > 64:
        raise ProtocolError("Invalid operation")

    params = request["params"]
    if not isinstance(params, dict):
        raise ProtocolError("Parameters must be an object")

    return request


def success_response(request_id: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": PROTOCOL_VERSION,
        "id": request_id,
        "ok": True,
        "result": result,
    }


def error_response(request_id: str | None, code: str) -> dict[str, Any]:
    return {
        "version": PROTOCOL_VERSION,
        "id": request_id,
        "ok": False,
        "error": {"code": code},
    }
