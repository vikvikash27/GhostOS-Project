
import json
import os
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch, MagicMock

from ghostcore import service
from ghostcore.config_store import GhostConfigStore
from ghostcore.identity import ProcessIdentity
from ghostprivacy.models import Capability


class GhostCoreServiceRuntimeTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.home = Path(self.temp_dir.name)

        self.state_root = (
            self.home / ".local" / "state" / "ghostos"
        )
        self.config_dir = self.state_root / "config"
        self.log_dir = self.state_root / "logs"

        self.config_path = self.config_dir / "ghostos.json"
        self.audit_path = self.log_dir / "security.jsonl"

        self.uid = os.getuid()
        self.pid = os.getpid()

        self.process = ProcessIdentity(
            pid=self.pid,
            uid=self.uid,
            gid=os.getgid(),
        )

        self.home_patch = patch(
            "ghostcore.service.Path.home",
            return_value=self.home,
        )
        self.home_patch.start()

        self.addCleanup(self.home_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)

    
    def save_config(self, privacy_decision="ALLOW"):
        config = {
            "schema_version": 1,
            "applications": [
                {
                    "application_id": "test.application",
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
            "network_rules": [],
        }

        self.state_root.mkdir(
            parents=True,
            exist_ok=True,
            mode=0o700,
        )
        self.state_root.chmod(0o700)

        self.config_dir.mkdir(
            exist_ok=True,
            mode=0o700,
        )
        self.config_dir.chmod(0o700)

        store = GhostConfigStore(self.config_path)
        store.save(config)


    def test_missing_configuration_uses_default_deny(self):
        runtime = service.create_default_runtime()

        application = runtime.registry.resolve(self.process)

        self.assertIsNone(application)

        with self.assertRaises(PermissionError):
            runtime.check_privacy(
                self.process,
                Capability.CAMERA,
            )

    def test_persisted_application_is_restored(self):
        self.save_config()

        runtime = service.create_default_runtime()

        application = runtime.registry.resolve(self.process)

        self.assertIsNotNone(application)
        self.assertEqual(
            application.application_id,
            "test.application",
        )
        self.assertEqual(application.uid, self.uid)

    def test_persisted_privacy_allow_rule_is_restored(self):
        self.save_config(privacy_decision="ALLOW")

        runtime = service.create_default_runtime()

        result = runtime.check_privacy(
            self.process,
            Capability.CAMERA,
        )

        self.assertEqual(result.decision.value, "allow")

    def test_persisted_privacy_deny_rule_is_restored(self):
        self.save_config(privacy_decision="DENY")

        runtime = service.create_default_runtime()

        result = runtime.check_privacy(
            self.process,
            Capability.CAMERA,
        )

        self.assertEqual(result.decision.value, "deny")

    def test_runtime_decisions_are_written_to_audit_log(self):
        self.save_config(privacy_decision="ALLOW")

        runtime = service.create_default_runtime()

        runtime.check_privacy(
            self.process,
            Capability.CAMERA,
        )

        self.assertTrue(self.audit_path.is_file())
        self.assertGreater(self.audit_path.stat().st_size, 0)

        with self.audit_path.open("r", encoding="utf-8") as file:
            event = json.loads(file.readline())

        self.assertIsInstance(event, dict)

    def test_invalid_configuration_prevents_runtime_startup(self):
        self.config_dir.mkdir(
            parents=True,
            exist_ok=True,
            mode=0o700,
        )

        self.config_path.write_text(
            "{ invalid json",
            encoding="utf-8",
        )
        self.config_path.chmod(0o600)

        with self.assertRaises(Exception):
            service.create_default_runtime()

    def test_insecure_state_directory_is_rejected(self):
        self.config_dir.mkdir(
            parents=True,
            exist_ok=True,
            mode=0o700,
        )

        self.config_dir.chmod(0o755)

        with self.assertRaises(PermissionError):
            service.create_default_runtime()

    def test_serve_passes_runtime_to_ipc_server(self):
        fake_runtime = object()
        fake_server = MagicMock()

        fake_server.serve_forever.side_effect = KeyboardInterrupt

        socket_path = self.home / "ghostcore.sock"

        with (
            patch(
                "ghostcore.service.create_default_runtime",
                return_value=fake_runtime,
            ),
            patch(
                "ghostcore.service.prepare_socket_path",
            ),
            patch(
                "ghostcore.service.GhostCoreServer",
                return_value=fake_server,
            ) as server_class,
            patch("ghostcore.service.os.chmod"),
            patch.object(Path, "unlink"),
        ):
            service.serve(socket_path)

        server_class.assert_called_once()

        self.assertIs(
            server_class.call_args.kwargs["runtime"],
            fake_runtime,
        )

        fake_server.serve_forever.assert_called_once()
        fake_server.server_close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
