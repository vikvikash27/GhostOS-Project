
"""GhostPrivacy policy evaluation with GhostGuard auditing."""

from ghostguard.audit import AuditLogger
from ghostguard.models import EventDecision, SecurityEvent

from .models import SecuritySubject
from .policy import PolicyEngine


class AuditedPrivacyPolicy:
    def __init__(
        self,
        engine: PolicyEngine,
        audit_logger: AuditLogger,
    ) -> None:
        self.engine = engine
        self.audit_logger = audit_logger

    def evaluate(self, subject: SecuritySubject, capability):
        result = self.engine.evaluate(subject, capability)

        decision = (
            EventDecision.ALLOW
            if result.decision.value == "allow"
            else EventDecision.DENY
        )

        event = SecurityEvent.create(
            source="ghostprivacy",
            event_type="permission_check",
            decision=decision,
            subject_uid=subject.uid,
            reason=result.reason,
        )

        # If recording fails, do not return the policy result.
        self.audit_logger.record(event)

        return result
