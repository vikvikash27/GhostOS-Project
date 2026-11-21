
"""Validated security event models."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
import json
import re
import uuid


class EventDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    INFO = "info"


@dataclass(frozen=True)
class SecurityEvent:
    event_id: str
    timestamp: str
    source: str
    event_type: str
    decision: EventDecision
    subject_uid: int | None
    reason: str
    correlation_id: str

    @classmethod
    def create(
        cls,
        source: str,
        event_type: str,
        decision: EventDecision,
        subject_uid: int | None = None,
        reason: str = "",
        correlation_id: str | None = None,
    ) -> "SecurityEvent":

        allowed_name = re.compile(r"^[a-zA-Z0-9_.-]{1,64}$")

        if not allowed_name.fullmatch(source):
            raise ValueError("Invalid event source")

        if not allowed_name.fullmatch(event_type):
            raise ValueError("Invalid event type")

        if subject_uid is not None:
            if isinstance(subject_uid, bool) or subject_uid < 0:
                raise ValueError("Invalid subject UID")

        if not isinstance(reason, str) or len(reason) > 256:
            raise ValueError("Invalid event reason")

        if correlation_id is None:
            correlation_id = str(uuid.uuid4())

        try:
            uuid.UUID(correlation_id)
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("Invalid correlation ID") from exc

        return cls(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            source=source,
            event_type=event_type,
            decision=decision,
            subject_uid=subject_uid,
            reason=reason,
            correlation_id=correlation_id,
        )

    def to_json(self) -> bytes:
        data = asdict(self)
        data["decision"] = self.decision.value

        return (
            json.dumps(data, separators=(",", ":"), sort_keys=True)
            .encode("utf-8")
            + b"\n"
        )
