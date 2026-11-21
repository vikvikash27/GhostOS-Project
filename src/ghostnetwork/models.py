
"""Network policy data models."""

from dataclasses import dataclass
from enum import Enum
import ipaddress


class NetworkCapability(str, Enum):
    INTERNET = "internet"
    LOCAL_NETWORK = "local_network"
    DNS = "dns"


class NetworkDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class NetworkSubject:
    uid: int
    pid: int

    def __post_init__(self) -> None:
        if isinstance(self.uid, bool) or self.uid < 0:
            raise ValueError("Invalid UID")

        if isinstance(self.pid, bool) or self.pid <= 0:
            raise ValueError("Invalid PID")


@dataclass(frozen=True)
class NetworkRule:
    uid: int
    capability: NetworkCapability
    decision: NetworkDecision
    destination: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.uid, bool) or self.uid < 0:
            raise ValueError("Invalid UID")

        if self.destination is not None:
            if not isinstance(self.destination, str):
                raise ValueError("Destination must be a string")

            try:
                ipaddress.ip_network(
                    self.destination,
                    strict=False,
                )
            except ValueError as exc:
                raise ValueError("Invalid destination network") from exc


@dataclass(frozen=True)
class NetworkPolicyResult:
    decision: NetworkDecision
    uid: int
    capability: NetworkCapability
    destination: str | None
    reason: str
