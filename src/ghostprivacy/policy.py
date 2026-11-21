
"""Default-deny capability-based policy engine."""

from __future__ import annotations

from collections.abc import Iterable

from .models import (
    Capability,
    Decision,
    PolicyResult,
    PolicyRule,
    SecuritySubject,
)


class PolicyEngine:
    """Evaluate permissions using OS-authenticated subject identities."""

    def __init__(self, rules: Iterable[PolicyRule] = ()) -> None:
        self._rules: dict[tuple[int, Capability], Decision] = {}

        for rule in rules:
            self.add_rule(rule)

    def add_rule(self, rule: PolicyRule) -> None:
        """Add or replace an exact UID/capability rule."""
        self._rules[(rule.uid, rule.capability)] = rule.decision

    def remove_rule(self, uid: int, capability: Capability) -> bool:
        """Remove a rule. Return whether a rule existed."""
        return self._rules.pop((uid, capability), None) is not None

    def evaluate(
        self,
        subject: SecuritySubject,
        capability: Capability,
    ) -> PolicyResult:
        """Evaluate a request. Missing rules are denied."""

        decision = self._rules.get(
            (subject.uid, capability),
            Decision.DENY,
        )

        if decision == Decision.ALLOW:
            reason = "explicit_policy_allow"
        else:
            reason = "explicit_policy_deny_or_no_matching_rule"

        return PolicyResult(
            decision=decision,
            subject_uid=subject.uid,
            capability=capability,
            reason=reason,
        )
