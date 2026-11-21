
import unittest

from ghostprivacy.models import (
    Capability,
    Decision,
    PolicyRule,
    SecuritySubject,
)
from ghostprivacy.policy import PolicyEngine


class PolicyEngineTests(unittest.TestCase):

    def setUp(self):
        self.subject = SecuritySubject(uid=1000, pid=1234)
        self.engine = PolicyEngine()

    def test_default_deny(self):
        result = self.engine.evaluate(
            self.subject,
            Capability.CAMERA,
        )

        self.assertEqual(result.decision, Decision.DENY)
        self.assertEqual(
            result.reason,
            "explicit_policy_deny_or_no_matching_rule",
        )

    def test_explicit_allow(self):
        self.engine.add_rule(
            PolicyRule(
                uid=1000,
                capability=Capability.CAMERA,
                decision=Decision.ALLOW,
            )
        )

        result = self.engine.evaluate(
            self.subject,
            Capability.CAMERA,
        )

        self.assertEqual(result.decision, Decision.ALLOW)

    def test_permissions_are_capability_specific(self):
        self.engine.add_rule(
            PolicyRule(
                uid=1000,
                capability=Capability.CAMERA,
                decision=Decision.ALLOW,
            )
        )

        result = self.engine.evaluate(
            self.subject,
            Capability.MICROPHONE,
        )

        self.assertEqual(result.decision, Decision.DENY)

    def test_permissions_are_uid_specific(self):
        self.engine.add_rule(
            PolicyRule(
                uid=1000,
                capability=Capability.CAMERA,
                decision=Decision.ALLOW,
            )
        )

        another_subject = SecuritySubject(uid=1001, pid=1235)

        result = self.engine.evaluate(
            another_subject,
            Capability.CAMERA,
        )

        self.assertEqual(result.decision, Decision.DENY)

    def test_explicit_deny_overrides_previous_allow(self):
        self.engine.add_rule(
            PolicyRule(1000, Capability.NETWORK, Decision.ALLOW)
        )
        self.engine.add_rule(
            PolicyRule(1000, Capability.NETWORK, Decision.DENY)
        )

        result = self.engine.evaluate(
            self.subject,
            Capability.NETWORK,
        )

        self.assertEqual(result.decision, Decision.DENY)

    def test_remove_rule(self):
        self.engine.add_rule(
            PolicyRule(1000, Capability.LOCATION, Decision.ALLOW)
        )

        removed = self.engine.remove_rule(1000, Capability.LOCATION)

        self.assertTrue(removed)
        self.assertEqual(
            self.engine.evaluate(
                self.subject,
                Capability.LOCATION,
            ).decision,
            Decision.DENY,
        )

    def test_invalid_subject_is_rejected(self):
        with self.assertRaises(ValueError):
            SecuritySubject(uid=-1, pid=1234)

    def test_invalid_pid_is_rejected(self):
        with self.assertRaises(ValueError):
            SecuritySubject(uid=1000, pid=0)


if __name__ == "__main__":
    unittest.main()
