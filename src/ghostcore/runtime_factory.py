
"""Build a GhostOS runtime from validated persistent configuration."""

from ghostguard.audit import AuditLogger
from ghostnetwork.models import (
    NetworkCapability,
    NetworkDecision,
    NetworkRule,
)
from ghostnetwork.policy import NetworkPolicyEngine
from ghostprivacy.models import Capability, Decision, PolicyRule
from ghostprivacy.policy import PolicyEngine

from .config_store import GhostConfigStore
from .identity import ApplicationIdentity, ApplicationRegistry
from .runtime import GhostOSRuntime


def build_runtime(
    config_store: GhostConfigStore,
    audit_logger: AuditLogger,
) -> GhostOSRuntime:
    """Load saved identities and policies into a new runtime.

    Invalid configuration raises ConfigError from the configuration store.
    No partially constructed runtime is returned.
    """
    config = config_store.load()

    registry = ApplicationRegistry()

    for item in config["applications"]:
        registry.register(
            ApplicationIdentity(
                application_id=item["application_id"],
                uid=item["uid"],
            )
        )

    privacy_rules = [
        PolicyRule(
            uid=item["uid"],
            capability=Capability[item["capability"]],
            decision=Decision[item["decision"]],
        )
        for item in config["privacy_rules"]
    ]

    network_rules = [
        NetworkRule(
            uid=item["uid"],
            capability=NetworkCapability[item["capability"]],
            decision=NetworkDecision[item["decision"]],
            destination=item["destination_cidr"],
        )
        for item in config["network_rules"]
    ]

    privacy_engine = PolicyEngine(privacy_rules)

    network_engine = NetworkPolicyEngine()
    for rule in network_rules:
        network_engine.add_rule(rule)

    return GhostOSRuntime(
        registry=registry,
        audit_logger=audit_logger,
        privacy_engine=privacy_engine,
        network_engine=network_engine,
    )
