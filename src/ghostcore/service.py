
"""Unprivileged GhostCore IPC service with runtime integration."""

from __future__ import annotations

import argparse
import os
import socket
import socketserver
import stat
import struct
from pathlib import Path
from typing import Any

from ghostguard.audit import AuditLogger
from ghostnetwork.models import NetworkCapability
from ghostprivacy.models import Capability

from .config_store import GhostConfigStore
from .identity import ProcessIdentity, get_peer_identity
from .protocol import (
    MAX_MESSAGE_BYTES,
    ProtocolError,
    decode_request,
    encode_message,
    error_response,
    success_response,
)
from .runtime_factory import build_runtime


IPC_READ_TIMEOUT_SECONDS = 5.0

SERVICE_NAME = "ghostcore"
SERVICE_VERSION = "0.2.0"


def default_socket_path() -> Path:
    state_dir = Path.home() / ".local" / "state" / "ghostos" / "run"
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    info = state_dir.stat()

    if info.st_uid != os.getuid():
        raise PermissionError(
            "GhostCore runtime directory has the wrong owner"
        )

    if stat.S_IMODE(info.st_mode) & 0o077:
        raise PermissionError(
            "GhostCore runtime directory must be private"
        )

    return state_dir / "ghostcore.sock"


class GhostCore:
    """Non-privileged health and service information."""

    def __init__(self) -> None:
        import time

        self.started_at = time.monotonic()

    def dispatch(
        self,
        operation: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        import time

        if operation != "health":
            raise ProtocolError("Unknown operation")

        if params:
            raise ProtocolError("health does not accept parameters")

        return {
            "service": SERVICE_NAME,
            "version": SERVICE_VERSION,
            "status": "healthy",
            "privileged": False,
            "uptime_seconds": round(
                time.monotonic() - self.started_at,
                3,
            ),
        }


class GhostCoreRequestHandler(socketserver.StreamRequestHandler):
    """Handle requests using credentials obtained from the kernel."""

    def handle(self) -> None:
        server = self.server
        assert isinstance(server, GhostCoreServer)

        try:
            peer = get_peer_identity(self.request)
        except (OSError, RuntimeError, ValueError, struct.error):
            self._send_error(None, "peer_credentials_unavailable")
            return

        try:
            self.request.settimeout(IPC_READ_TIMEOUT_SECONDS)
            raw = self.rfile.readline(MAX_MESSAGE_BYTES + 1)
        except (OSError, socket.timeout):
            # The client disconnected or exceeded the read timeout.
            return

        if len(raw) > MAX_MESSAGE_BYTES:
            self._send_error(None, "message_too_large")
            return

        request_id: str | None = None

        try:
            request = decode_request(raw)
            request_id = request["id"]

            operation = request["operation"]
            params = request["params"]

            if operation == "health":
                result = server.core.dispatch(operation, params)

            elif operation == "privacy.check":
                result = self._privacy_check(server, peer, params)

            elif operation == "network.check":
                result = self._network_check(server, peer, params)

            else:
                raise ProtocolError("Unknown operation")

            response = success_response(request_id, result)

        except PermissionError:
            response = error_response(
                request_id,
                "peer_not_authorized",
            )

        except (ProtocolError, ValueError, TypeError, KeyError):
            response = error_response(
                request_id,
                "invalid_request",
            )

        except Exception:
            # Do not disclose internal errors or secrets through IPC.
            response = error_response(
                request_id,
                "internal_error",
            )

        self._send_response(response)

    @staticmethod
    def _privacy_check(
        server: GhostCoreServer,
        peer: ProcessIdentity,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        if server.runtime is None:
            raise ProtocolError("Security runtime is unavailable")

        if set(params) != {"capability"}:
            raise ProtocolError("Invalid privacy parameters")

        capability = Capability(params["capability"])
        result = server.runtime.check_privacy(peer, capability)

        return {
            "decision": result.decision.value,
            "capability": result.capability.value,
            "reason": result.reason,
            "subject_uid": result.subject_uid,
        }

    @staticmethod
    def _network_check(
        server: GhostCoreServer,
        peer: ProcessIdentity,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        if server.runtime is None:
            raise ProtocolError("Security runtime is unavailable")

        allowed = {"capability", "destination"}

        if not set(params).issubset(allowed) or "capability" not in params:
            raise ProtocolError("Invalid network parameters")

        destination = params.get("destination")

        if destination is not None and not isinstance(destination, str):
            raise ProtocolError("Destination must be a string")

        capability = NetworkCapability(params["capability"])

        result = server.runtime.check_network(
            peer,
            capability,
            destination,
        )

        return {
            "decision": result.decision.value,
            "capability": result.capability.value,
            "destination": result.destination,
            "reason": result.reason,
            "subject_uid": result.uid,
        }

    def _send_response(self, response: dict[str, Any]) -> None:
        try:
            self.wfile.write(encode_message(response))
            self.wfile.flush()
        except (BrokenPipeError, OSError):
            pass

    def _send_error(
        self,
        request_id: str | None,
        code: str,
    ) -> None:
        self._send_response(error_response(request_id, code))


class GhostCoreServer(
    socketserver.ThreadingMixIn,
    socketserver.UnixStreamServer,
):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(
        self,
        socket_path: Path,
        core: GhostCore,
        runtime=None,
    ) -> None:
        self.socket_path = socket_path
        self.core = core
        self.runtime = runtime

        super().__init__(
            str(socket_path),
            GhostCoreRequestHandler,
        )


def prepare_socket_path(path: Path) -> None:
    if not path.parent.is_dir():
        raise FileNotFoundError(
            "Socket parent directory does not exist"
        )

    parent_info = path.parent.stat()

    if parent_info.st_uid != os.getuid():
        raise PermissionError(
            "Socket directory has the wrong owner"
        )

    if stat.S_IMODE(parent_info.st_mode) & 0o077:
        raise PermissionError(
            "Socket directory must be private"
        )

    try:
        existing = path.lstat()
    except FileNotFoundError:
        return

    if not stat.S_ISSOCK(existing.st_mode):
        raise FileExistsError(
            "Refusing to replace a non-socket path"
        )

    if existing.st_uid != os.getuid():
        raise PermissionError(
            "Socket has the wrong owner"
        )

    path.unlink()


def create_default_runtime():
    """Load persistent policy configuration and initialize the security runtime."""

    state_root = Path.home() / ".local" / "state" / "ghostos"
    config_dir = state_root / "config"
    log_dir = state_root / "logs"

    for directory in (state_root, config_dir, log_dir):
        directory.mkdir(
            parents=True,
            exist_ok=True,
            mode=0o700,
        )

        info = directory.lstat()

        if not stat.S_ISDIR(info.st_mode):
            raise PermissionError(
                f"GhostCore state path is not a directory: {directory}"
            )

        if info.st_uid != os.getuid():
            raise PermissionError(
                f"GhostCore state directory has the wrong owner: {directory}"
            )

        if stat.S_IMODE(info.st_mode) & 0o077:
            raise PermissionError(
                f"GhostCore state directory must be private: {directory}"
            )

    config_path = config_dir / "ghostos.json"
    audit_path = log_dir / "security.jsonl"

    config_store = GhostConfigStore(config_path)
    audit_logger = AuditLogger(audit_path)

    return build_runtime(config_store, audit_logger)


def serve(socket_path: Path) -> None:
    if os.geteuid() == 0:
        raise PermissionError(
            "GhostCore must not run as root"
        )

    # Initialize the security runtime before opening the IPC socket.
    # Invalid or unsafe configuration must prevent service startup.
    runtime = create_default_runtime()

    prepare_socket_path(socket_path)

    server = GhostCoreServer(
        socket_path,
        GhostCore(),
        runtime=runtime,
    )

    os.chmod(socket_path, 0o600)

    print(f"GhostCore listening at {socket_path}")
    print("Privilege mode: unprivileged")
    print("Runtime integration: configured")
    print("Persistent policy: loaded")
    print("Audit logging: enabled")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever(poll_interval=0.5)

    except KeyboardInterrupt:
        print("\nStopping GhostCore...")

    finally:
        server.server_close()

        try:
            socket_path.unlink()
        except FileNotFoundError:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GhostCore IPC service"
    )

    parser.add_argument(
        "--socket",
        type=Path,
        default=default_socket_path(),
    )

    args = parser.parse_args()
    serve(args.socket)


if __name__ == "__main__":
    main()
