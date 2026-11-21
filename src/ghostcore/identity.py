
"""OS-authenticated process identity and application registry."""

from __future__ import annotations

import socket
import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    uid: int
    gid: int

    def __post_init__(self) -> None:
        for name, value in (
            ("pid", self.pid),
            ("uid", self.uid),
            ("gid", self.gid),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"Invalid {name}")

        if self.pid <= 0 or self.uid < 0 or self.gid < 0:
            raise ValueError("Invalid process credentials")


def get_peer_identity(connection: socket.socket) -> ProcessIdentity:
    """Read credentials supplied by the Linux kernel via SO_PEERCRED."""
    if not hasattr(socket, "SO_PEERCRED"):
        raise RuntimeError("SO_PEERCRED is unavailable on this platform")

    raw = connection.getsockopt(
        socket.SOL_SOCKET,
        socket.SO_PEERCRED,
        struct.calcsize("3i"),
    )

    pid, uid, gid = struct.unpack("3i", raw)

    return ProcessIdentity(pid=pid, uid=uid, gid=gid)


@dataclass(frozen=True)
class ApplicationIdentity:
    application_id: str
    uid: int


class ApplicationRegistry:
    """Resolve OS UIDs to registered GhostOS application identities."""

    def __init__(self) -> None:
        self._applications: dict[int, ApplicationIdentity] = {}

    def register(self, application: ApplicationIdentity) -> None:
        if not application.application_id:
            raise ValueError("Application ID cannot be empty")

        if len(application.application_id) > 128:
            raise ValueError("Application ID is too long")

        if application.uid < 0:
            raise ValueError("Invalid application UID")

        if application.uid in self._applications:
            raise ValueError("UID is already registered")

        self._applications[application.uid] = application

    def resolve(self, identity: ProcessIdentity) -> ApplicationIdentity | None:
        return self._applications.get(identity.uid)
