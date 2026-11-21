
"""GhostOS security policy integration runtime."""

from ghostguard.audit import AuditLogger
from ghostnetwork.audited import AuditedNetworkPolicy
from ghostnetwork.models import NetworkCapability, NetworkSubject
from ghostnetwork.policy import NetworkPolicyEngine
from ghostprivacy.audited import AuditedPrivacyPolicy
from ghostprivacy.models import Capability, SecuritySubject
from ghostprivacy.policy import PolicyEngine

from .identity import ApplicationRegistry, ProcessIdentity


class GhostOSRuntime:
    """Connect process identities with privacy and network policies."""

    def __init__(
        self,
        registry: ApplicationRegistry,
        audit_logger: AuditLogger,
        privacy_engine: PolicyEngine,
        network_engine: NetworkPolicyEngine,
    ) -> None:
        self.registry = registry

        self.privacy = AuditedPrivacyPolicy(
            privacy_engine,
            audit_logger,
        )

        self.network = AuditedNetworkPolicy(
            network_engine,
            audit_logger,
        )

    def check_privacy(
        self,
        process: ProcessIdentity,
        capability: Capability,
    ):
        application = self.registry.resolve(process)

        if application is None:
            raise PermissionError("Unregistered application")

        subject = SecuritySubject(
            uid=process.uid,
            pid=process.pid,
        )

        return self.privacy.evaluate(subject, capability)

    def check_network(
        self,
        process: ProcessIdentity,
        capability: NetworkCapability,
        destination: str | None = None,
    ):
        application = self.registry.resolve(process)

        if application is None:
            raise PermissionError("Unregistered application")

        subject = NetworkSubject(
            uid=process.uid,
            pid=process.pid,
        )

        return self.network.evaluate(
            subject,
            capability,
            destination,
        )
