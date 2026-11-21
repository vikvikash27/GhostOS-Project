
"""Command-line client for the GhostCore IPC service."""

from __future__ import annotations

import argparse
import json
import socket
import uuid
from pathlib import Path
from typing import Any

from .protocol import (
    PROTOCOL_VERSION,
    decode_request,
    encode_message,
)


def default_socket_path() -> Path:
    return (
        Path.home()
        / ".local"
        / "state"
        / "ghostos"
        / "run"
        / "ghostcore.sock"
    )


def request(
    socket_path: Path,
    operation: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    message = {
        "version": PROTOCOL_VERSION,
        "id": str(uuid.uuid4()),
        "operation": operation,
        "params": params or {},
    }

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(5.0)
        connection.connect(str(socket_path))
        connection.sendall(encode_message(message))

        with connection.makefile("rb") as response_file:
            raw_response = response_file.readline(65_537)

    if len(raw_response) > 65_536 or not raw_response.endswith(b"\n"):
        raise RuntimeError("Invalid response from GhostCore")

    try:
        response = json.loads(raw_response.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("GhostCore returned invalid JSON") from exc

    if not isinstance(response, dict):
        raise RuntimeError("GhostCore returned an invalid response")

    return response


def main() -> None:
    parser = argparse.ArgumentParser(description="GhostCore client")
    parser.add_argument("--socket", type=Path, default=default_socket_path())
    parser.add_argument("operation", choices=["health"])
    args = parser.parse_args()

    response = request(args.socket, args.operation)
    print(json.dumps(response, indent=2))

    if not response.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
