
"""GhostNetwork policy evaluation with GhostGuard auditing."""

from ghostguard.audit import AuditLogger
from ghostguard.models import EventDecision, SecurityEvent

from .models import NetworkSubject
from .policy import NetworkPolicyEngine


class AuditedNetworkPolicy:
    def __init__(
        self,
        engine: NetworkPolicyEngine,
        audit_logger: AuditLogger,
    ) -> None:
        self.engine = engine
        self.audit_logger = audit_logger

    def evaluate(
        self,
        subject: NetworkSubject,
        capability,
        destination: str | None = None,
    ):
        result = self.engine.evaluate(
            subject,
            capability,
            destination,
        )

        decision = (
            EventDecision.ALLOW
            if result.decision.value == "allow"
            else EventDecision.DENY
        )

        event = SecurityEvent.create(
            source="ghostnetwork",
            event_type="network_check",
            decision=decision,
            subject_uid=subject.uid,
            reason=result.reason,
        )

        # Do not return an authorization result if auditing fails.
        self.audit_logger.record(event)

        return result
