
import json
import tempfile
import unittest
from pathlib import Path

from ghostcore.identity import (
    ApplicationIdentity,
    ApplicationRegistry,
    ProcessIdentity,
)
from ghostcore.runtime import GhostOSRuntime
from ghostguard.audit import AuditLogger
from ghostnetwork.models import (
    NetworkCapability,
    NetworkDecision,
    NetworkRule,
)
from ghostnetwork.policy import NetworkPolicyEngine
from ghostprivacy.models import Capability, Decision, PolicyRule
from ghostprivacy.policy import PolicyEngine


class GhostOSRuntimeTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        directory = Path(self.temp.name)
        self.logger = AuditLogger(directory / "events.jsonl")

        self.registry = ApplicationRegistry()
        self.registry.register(
            ApplicationIdentity("com.ghostos.browser", 1000)
        )

        self.privacy_engine = PolicyEngine()
        self.network_engine = NetworkPolicyEngine()

        self.runtime = GhostOSRuntime(
            registry=self.registry,
            audit_logger=self.logger,
            privacy_engine=self.privacy_engine,
            network_engine=self.network_engine,
        )

        self.process = ProcessIdentity(
            pid=1234,
            uid=1000,
            gid=1000,
        )

    def test_privacy_decision_is_audited(self):
        self.privacy_engine.add_rule(
            PolicyRule(1000, Capability.CAMERA, Decision.ALLOW)
        )

        result = self.runtime.check_privacy(
            self.process,
            Capability.CAMERA,
        )

        self.assertEqual(result.decision, Decision.ALLOW)

        event = json.loads(self.logger.log_path.read_text().splitlines()[0])
        self.assertEqual(event["source"], "ghostprivacy")

    def test_network_decision_is_audited(self):
        self.network_engine.add_rule(
            NetworkRule(
                1000,
                NetworkCapability.INTERNET,
                NetworkDecision.ALLOW,
            )
        )

        result = self.runtime.check_network(
            self.process,
            NetworkCapability.INTERNET,
        )

        self.assertEqual(result.decision, NetworkDecision.ALLOW)

        event = json.loads(self.logger.log_path.read_text().splitlines()[0])
        self.assertEqual(event["source"], "ghostnetwork")

    def test_unregistered_application_is_rejected(self):
        unknown = ProcessIdentity(
            pid=1235,
            uid=2000,
            gid=2000,
        )

        with self.assertRaises(PermissionError):
            self.runtime.check_privacy(
                unknown,
                Capability.CAMERA,
            )

    def test_denied_privacy_request_is_audited(self):
        result = self.runtime.check_privacy(
            self.process,
            Capability.MICROPHONE,
        )

        self.assertEqual(result.decision, Decision.DENY)

        event = json.loads(self.logger.log_path.read_text().splitlines()[0])
        self.assertEqual(event["decision"], "deny")


if __name__ == "__main__":
    unittest.main()
