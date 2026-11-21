
"""Private JSONL audit event storage."""

from __future__ import annotations

import os
import stat
import threading
from pathlib import Path

from .models import SecurityEvent

MAX_EVENT_BYTES = 4096


def default_log_path() -> Path:
    return (
        Path.home()
        / ".local"
        / "state"
        / "ghostos"
        / "audit"
        / "events.jsonl"
    )


class AuditLogger:
    """Write validated security events to a private local log."""

    def __init__(self, log_path: Path | None = None) -> None:
        self.log_path = log_path or default_log_path()
        self._lock = threading.Lock()

        self.log_path.parent.mkdir(
            parents=True,
            exist_ok=True,
            mode=0o700,
        )

        directory_info = self.log_path.parent.stat()

        if directory_info.st_uid != os.getuid():
            raise PermissionError("Audit directory has the wrong owner")

        if stat.S_IMODE(directory_info.st_mode) & 0o077:
            raise PermissionError("Audit directory must be private")

        self._validate_existing_file()

    def _validate_existing_file(self) -> None:
        try:
            info = self.log_path.lstat()
        except FileNotFoundError:
            return

        if not stat.S_ISREG(info.st_mode):
            raise PermissionError("Audit path must be a regular file")

        if info.st_uid != os.getuid():
            raise PermissionError("Audit file has the wrong owner")

        if stat.S_IMODE(info.st_mode) & 0o077:
            raise PermissionError("Audit file must be private")

    def record(self, event: SecurityEvent) -> None:
        """Append one event without following symlinks."""

        payload = event.to_json()

        if len(payload) > MAX_EVENT_BYTES:
            raise ValueError("Audit event exceeds size limit")

        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
        flags |= getattr(os, "O_NOFOLLOW", 0)
        flags |= getattr(os, "O_CLOEXEC", 0)

        with self._lock:
            fd = os.open(self.log_path, flags, 0o600)

            try:
                info = os.fstat(fd)

                if not stat.S_ISREG(info.st_mode):
                    raise PermissionError("Audit target is not a regular file")

                if info.st_uid != os.getuid():
                    raise PermissionError("Audit target has the wrong owner")

                if stat.S_IMODE(info.st_mode) & 0o077:
                    raise PermissionError("Audit target must be private")

                written = os.write(fd, payload)

                if written != len(payload):
                    raise OSError("Incomplete audit event write")

            finally:
                os.close(fd)
