
import json
import tempfile
import unittest
from pathlib import Path

from ghostguard.audit import AuditLogger
from ghostnetwork.audited import AuditedNetworkPolicy
from ghostnetwork.models import (
    NetworkCapability,
    NetworkDecision,
    NetworkRule,
    NetworkSubject,
)
from ghostnetwork.policy import NetworkPolicyEngine


class AuditedNetworkTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        directory = Path(self.temp.name)
        self.logger = AuditLogger(directory / "events.jsonl")
        self.engine = NetworkPolicyEngine()
        self.policy = AuditedNetworkPolicy(self.engine, self.logger)
        self.subject = NetworkSubject(uid=1000, pid=1234)

    def test_allow_decision_is_audited(self):
        self.engine.add_rule(
            NetworkRule(
                1000,
                NetworkCapability.INTERNET,
                NetworkDecision.ALLOW,
            )
        )

        result = self.policy.evaluate(
            self.subject,
            NetworkCapability.INTERNET,
        )

        self.assertEqual(result.decision, NetworkDecision.ALLOW)

        event = json.loads(self.logger.log_path.read_text().splitlines()[0])
        self.assertEqual(event["source"], "ghostnetwork")
        self.assertEqual(event["decision"], "allow")

    def test_deny_decision_is_audited(self):
        result = self.policy.evaluate(
            self.subject,
            NetworkCapability.INTERNET,
        )

        self.assertEqual(result.decision, NetworkDecision.DENY)

        event = json.loads(self.logger.log_path.read_text().splitlines()[0])
        self.assertEqual(event["decision"], "deny")


if __name__ == "__main__":
    unittest.main()
