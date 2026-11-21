
import os
import tempfile
import unittest
from pathlib import Path

from ghostcore.config_store import GhostConfigStore
from ghostcore.identity import ProcessIdentity
from ghostcore.runtime_factory import build_runtime
from ghostguard.audit import AuditLogger
from ghostnetwork.models import NetworkCapability, NetworkDecision
from ghostprivacy.models import Capability, Decision


class RuntimeFactoryTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp_dir.name)
        os.chmod(self.directory, 0o700)

        self.config_store = GhostConfigStore(
            self.directory / "config.json"
        )
        self.audit_logger = AuditLogger(
            self.directory / "audit.jsonl"
        )

        self.uid = os.getuid()
        self.process = ProcessIdentity(
            pid=os.getpid(),
            uid=self.uid,
            gid=os.getgid(),
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def save_config(self, privacy_decision="ALLOW",
                    network_decision="ALLOW"):
        config = {
            "schema_version": 1,
            "applications": [
                {
                    "application_id": "ghost.test",
                    "uid": self.uid,
                }
            ],
            "privacy_rules": [
                {
                    "uid": self.uid,
                    "capability": "CAMERA",
                    "decision": privacy_decision,
                }
            ],
            "network_rules": [
                {
                    "uid": self.uid,
                    "capability": "INTERNET",
                    "decision": network_decision,
                    "destination_cidr": "192.0.2.0/24",
                }
            ],
        }
        self.config_store.save(config)

    def test_application_registry_is_restored(self):
        self.save_config()
        runtime = build_runtime(
            self.config_store,
            self.audit_logger,
        )

        application = runtime.registry.resolve(self.process)

        self.assertIsNotNone(application)
        self.assertEqual(application.application_id, "ghost.test")
        self.assertEqual(application.uid, self.uid)

    def test_privacy_allow_rule_is_restored(self):
        self.save_config()
        runtime = build_runtime(
            self.config_store,
            self.audit_logger,
        )

        result = runtime.check_privacy(
            self.process,
            Capability.CAMERA,
        )

        self.assertEqual(result.decision, Decision.ALLOW)

    def test_network_cidr_rule_is_restored(self):
        self.save_config()
        runtime = build_runtime(
            self.config_store,
            self.audit_logger,
        )

        result = runtime.check_network(
            self.process,
            NetworkCapability.INTERNET,
            "192.0.2.10",
        )

        self.assertEqual(result.decision, NetworkDecision.ALLOW)

    def test_saved_deny_rules_remain_denied(self):
        self.save_config(
            privacy_decision="DENY",
            network_decision="DENY",
        )
        runtime = build_runtime(
            self.config_store,
            self.audit_logger,
        )

        privacy_result = runtime.check_privacy(
            self.process,
            Capability.CAMERA,
        )
        network_result = runtime.check_network(
            self.process,
            NetworkCapability.INTERNET,
            "192.0.2.10",
        )

        self.assertEqual(privacy_result.decision, Decision.DENY)
        self.assertEqual(network_result.decision, NetworkDecision.DENY)


if __name__ == "__main__":
    unittest.main()
