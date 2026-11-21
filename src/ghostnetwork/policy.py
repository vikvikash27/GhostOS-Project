
"""Default-deny per-application network policy engine."""

from __future__ import annotations

import ipaddress

from .models import (
    NetworkCapability,
    NetworkDecision,
    NetworkPolicyResult,
    NetworkRule,
    NetworkSubject,
)


class NetworkPolicyEngine:
    """Evaluate network access using OS-authenticated UID identities."""

    def __init__(self) -> None:
        self._rules: dict[
            tuple[int, NetworkCapability, str | None],
            NetworkDecision,
        ] = {}

    def add_rule(self, rule: NetworkRule) -> None:
        key = (rule.uid, rule.capability, rule.destination)
        self._rules[key] = rule.decision

    def remove_rule(
        self,
        uid: int,
        capability: NetworkCapability,
        destination: str | None = None,
    ) -> bool:
        key = (uid, capability, destination)
        return self._rules.pop(key, None) is not None

    def evaluate(
        self,
        subject: NetworkSubject,
        capability: NetworkCapability,
        destination: str | None = None,
    ) -> NetworkPolicyResult:

        if destination is not None:
            try:
                target = ipaddress.ip_address(destination)
            except ValueError as exc:
                raise ValueError("Destination must be an IP address") from exc
        else:
            target = None

        # An exact destination rule takes precedence over a general
        # capability rule. Missing rules are denied.
        decision = self._rules.get(
            (subject.uid, capability, destination)
        )

        reason = "exact_destination_rule"

        if decision is None and target is not None:
            matching_rules = []

            for (uid, rule_capability, network), rule_decision in (
                self._rules.items()
            ):
                if (
                    uid == subject.uid
                    and rule_capability == capability
                    and network is not None
                    and target in ipaddress.ip_network(network)
                ):
                    matching_rules.append(
                        (ipaddress.ip_network(network).prefixlen, rule_decision)
                    )

            if matching_rules:
                # Most specific matching network wins.
                matching_rules.sort(key=lambda item: item[0], reverse=True)
                decision = matching_rules[0][1]
                reason = "destination_network_rule"

        if decision is None:
            decision = self._rules.get(
                (subject.uid, capability, None)
            )
            reason = "general_capability_rule"

        if decision is None:
            decision = NetworkDecision.DENY
            reason = "no_matching_rule"

        return NetworkPolicyResult(
            decision=decision,
            uid=subject.uid,
            capability=capability,
            destination=destination,
            reason=reason,
        )
