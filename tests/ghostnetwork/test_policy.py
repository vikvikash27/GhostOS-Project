
import unittest

from ghostnetwork.models import (
    NetworkCapability,
    NetworkDecision,
    NetworkRule,
    NetworkSubject,
)
from ghostnetwork.policy import NetworkPolicyEngine


class NetworkPolicyTests(unittest.TestCase):

    def setUp(self):
        self.engine = NetworkPolicyEngine()
        self.subject = NetworkSubject(uid=1000, pid=1234)

    def test_default_deny(self):
        result = self.engine.evaluate(
            self.subject,
            NetworkCapability.INTERNET,
        )

        self.assertEqual(result.decision, NetworkDecision.DENY)

    def test_explicit_allow(self):
        self.engine.add_rule(
            NetworkRule(
                uid=1000,
                capability=NetworkCapability.INTERNET,
                decision=NetworkDecision.ALLOW,
            )
        )

        result = self.engine.evaluate(
            self.subject,
            NetworkCapability.INTERNET,
        )

        self.assertEqual(result.decision, NetworkDecision.ALLOW)

    def test_uid_isolation(self):
        self.engine.add_rule(
            NetworkRule(
                uid=1000,
                capability=NetworkCapability.INTERNET,
                decision=NetworkDecision.ALLOW,
            )
        )

        another = NetworkSubject(uid=1001, pid=1235)

        result = self.engine.evaluate(
            another,
            NetworkCapability.INTERNET,
        )

        self.assertEqual(result.decision, NetworkDecision.DENY)

    def test_capability_isolation(self):
        self.engine.add_rule(
            NetworkRule(
                uid=1000,
                capability=NetworkCapability.INTERNET,
                decision=NetworkDecision.ALLOW,
            )
        )

        result = self.engine.evaluate(
            self.subject,
            NetworkCapability.DNS,
        )

        self.assertEqual(result.decision, NetworkDecision.DENY)

    def test_destination_network_allow(self):
        self.engine.add_rule(
            NetworkRule(
                uid=1000,
                capability=NetworkCapability.INTERNET,
                decision=NetworkDecision.ALLOW,
                destination="192.168.1.0/24",
            )
        )

        result = self.engine.evaluate(
            self.subject,
            NetworkCapability.INTERNET,
            "192.168.1.20",
        )

        self.assertEqual(result.decision, NetworkDecision.ALLOW)
        self.assertEqual(result.reason, "destination_network_rule")

    def test_destination_network_deny(self):
        self.engine.add_rule(
            NetworkRule(
                uid=1000,
                capability=NetworkCapability.INTERNET,
                decision=NetworkDecision.DENY,
                destination="10.0.0.0/8",
            )
        )

        result = self.engine.evaluate(
            self.subject,
            NetworkCapability.INTERNET,
            "10.1.2.3",
        )

        self.assertEqual(result.decision, NetworkDecision.DENY)

    def test_more_specific_network_rule_wins(self):
        self.engine.add_rule(
            NetworkRule(
                uid=1000,
                capability=NetworkCapability.INTERNET,
                decision=NetworkDecision.DENY,
                destination="192.168.0.0/16",
            )
        )
        self.engine.add_rule(
            NetworkRule(
                uid=1000,
                capability=NetworkCapability.INTERNET,
                decision=NetworkDecision.ALLOW,
                destination="192.168.1.0/24",
            )
        )

        result = self.engine.evaluate(
            self.subject,
            NetworkCapability.INTERNET,
            "192.168.1.20",
        )

        self.assertEqual(result.decision, NetworkDecision.ALLOW)

    def test_general_rule_applies_when_no_destination_rule_matches(self):
        self.engine.add_rule(
            NetworkRule(
                uid=1000,
                capability=NetworkCapability.INTERNET,
                decision=NetworkDecision.ALLOW,
            )
        )

        result = self.engine.evaluate(
            self.subject,
            NetworkCapability.INTERNET,
            "8.8.8.8",
        )

        self.assertEqual(result.decision, NetworkDecision.ALLOW)
        self.assertEqual(result.reason, "general_capability_rule")

    def test_invalid_destination_is_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.evaluate(
                self.subject,
                NetworkCapability.INTERNET,
                "not-an-ip-address",
            )

    def test_invalid_network_is_rejected(self):
        with self.assertRaises(ValueError):
            NetworkRule(
                uid=1000,
                capability=NetworkCapability.INTERNET,
                decision=NetworkDecision.ALLOW,
                destination="invalid-network",
            )

    def test_remove_rule(self):
        self.engine.add_rule(
            NetworkRule(
                uid=1000,
                capability=NetworkCapability.DNS,
                decision=NetworkDecision.ALLOW,
            )
        )

        removed = self.engine.remove_rule(
            1000,
            NetworkCapability.DNS,
        )

        self.assertTrue(removed)

        result = self.engine.evaluate(
            self.subject,
            NetworkCapability.DNS,
        )

        self.assertEqual(result.decision, NetworkDecision.DENY)


if __name__ == "__main__":
    unittest.main()
