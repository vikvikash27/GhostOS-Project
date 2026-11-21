
"""Data models for GhostPrivacy."""

from dataclasses import dataclass
from enum import Enum


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class Capability(str, Enum):
    CAMERA = "camera"
    MICROPHONE = "microphone"
    LOCATION = "location"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    NETWORK = "network"


@dataclass(frozen=True)
class SecuritySubject:
    """Identity obtained from the operating system."""
    uid: int
    pid: int

    def __post_init__(self) -> None:
        if self.uid < 0:
            raise ValueError("UID cannot be negative")
        if self.pid <= 0:
            raise ValueError("PID must be positive")


@dataclass(frozen=True)
class PolicyRule:
    uid: int
    capability: Capability
    decision: Decision

    def __post_init__(self) -> None:
        if self.uid < 0:
            raise ValueError("UID cannot be negative")


@dataclass(frozen=True)
class PolicyResult:
    decision: Decision
    subject_uid: int
    capability: Capability
    reason: str
