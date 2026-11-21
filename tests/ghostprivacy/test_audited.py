
import json
import tempfile
import unittest
from pathlib import Path

from ghostguard.audit import AuditLogger
from ghostprivacy.audited import AuditedPrivacyPolicy
from ghostprivacy.models import (
    Capability,
    Decision,
    PolicyRule,
    SecuritySubject,
)
from ghostprivacy.policy import PolicyEngine


class AuditedPrivacyTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        directory = Path(self.temp.name)
        self.logger = AuditLogger(directory / "events.jsonl")
        self.engine = PolicyEngine()
        self.policy = AuditedPrivacyPolicy(self.engine, self.logger)
        self.subject = SecuritySubject(uid=1000, pid=1234)

    def test_allow_decision_is_audited(self):
        self.engine.add_rule(
            PolicyRule(1000, Capability.CAMERA, Decision.ALLOW)
        )

        result = self.policy.evaluate(self.subject, Capability.CAMERA)

        self.assertEqual(result.decision, Decision.ALLOW)

        event = json.loads(
            (self.logger.log_path).read_text().splitlines()[0]
        )
        self.assertEqual(event["source"], "ghostprivacy")
        self.assertEqual(event["decision"], "allow")

    def test_deny_decision_is_audited(self):
        result = self.policy.evaluate(self.subject, Capability.MICROPHONE)

        self.assertEqual(result.decision, Decision.DENY)

        event = json.loads(self.logger.log_path.read_text().splitlines()[0])
        self.assertEqual(event["decision"], "deny")


if __name__ == "__main__":
    unittest.main()
