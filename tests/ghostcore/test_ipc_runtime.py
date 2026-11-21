
import json
import os
import socket
import tempfile
import threading
import unittest
from pathlib import Path

from ghostcore.identity import (
    ApplicationIdentity,
    ApplicationRegistry,
)
from ghostcore.runtime import GhostOSRuntime
from ghostcore.service import GhostCore, GhostCoreServer
from ghostcore.protocol import MAX_MESSAGE_BYTES
from ghostguard.audit import AuditLogger
from ghostnetwork.policy import NetworkPolicyEngine
from ghostprivacy.policy import PolicyEngine


class AuthenticatedIPCTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        directory = Path(self.temp.name)
        os.chmod(directory, 0o700)

        self.socket_path = directory / "ghostcore.sock"
        self.log_path = directory / "events.jsonl"

        self.registry = ApplicationRegistry()
        self.registry.register(
            ApplicationIdentity(
                application_id="com.ghostos.test",
                uid=os.getuid(),
            )
        )

        self.logger = AuditLogger(self.log_path)

        self.runtime = GhostOSRuntime(
            registry=self.registry,
            audit_logger=self.logger,
            privacy_engine=PolicyEngine(),
            network_engine=NetworkPolicyEngine(),
        )

        self.server = GhostCoreServer(
            self.socket_path,
            GhostCore(),
            runtime=self.runtime,
        )

        os.chmod(self.socket_path, 0o600)

        self.thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True,
        )
        self.thread.start()

        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def send_request(self, request):
        payload = json.dumps(request).encode("utf-8") + b"\n"

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(3)
            client.connect(str(self.socket_path))
            client.sendall(payload)

            with client.makefile("rb") as response_file:
                response = response_file.readline(MAX_MESSAGE_BYTES + 1)

        return json.loads(response.decode("utf-8"))

    def send_raw_request(self, payload):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(3)
            client.connect(str(self.socket_path))
            client.sendall(payload)

            # Signal that no more request bytes will be sent.
            client.shutdown(socket.SHUT_WR)

            with client.makefile("rb") as response_file:
                response = response_file.readline(MAX_MESSAGE_BYTES + 1)

        return json.loads(response.decode("utf-8"))

    def test_privacy_request_uses_kernel_identity(self):
        response = self.send_request({
            "version": 1,
            "id": "ipc-test-1",
            "operation": "privacy.check",
            "params": {"capability": "camera"},
        })

        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["decision"], "deny")
        self.assertEqual(
            response["result"]["subject_uid"],
            os.getuid(),
        )

    def test_network_request_is_audited(self):
        response = self.send_request({
            "version": 1,
            "id": "ipc-test-2",
            "operation": "network.check",
            "params": {
                "capability": "internet",
                "destination": "8.8.8.8",
            },
        })

        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["decision"], "deny")

        lines = self.log_path.read_text().splitlines()
        self.assertEqual(len(lines), 1)

        event = json.loads(lines[0])
        self.assertEqual(event["source"], "ghostnetwork")

    def test_client_cannot_supply_uid(self):
        response = self.send_request({
            "version": 1,
            "id": "ipc-test-3",
            "operation": "privacy.check",
            "params": {"capability": "camera"},
            "uid": 0,
        })

        self.assertFalse(response["ok"])
        self.assertEqual(
            response["error"]["code"],
            "invalid_request",
        )

    def test_identity_override_in_parameters_is_rejected(self):
        response = self.send_request({
            "version": 1,
            "id": "ipc-test-identity",
            "operation": "privacy.check",
            "params": {
                "capability": "camera",
                "uid": 0,
            },
        })

        self.assertFalse(response["ok"])
        self.assertEqual(
            response["error"]["code"],
            "invalid_request",
        )

    def test_unknown_operation_is_rejected(self):
        response = self.send_request({
            "version": 1,
            "id": "ipc-test-4",
            "operation": "root.execute",
            "params": {},
        })

        self.assertFalse(response["ok"])
        self.assertEqual(
            response["error"]["code"],
            "invalid_request",
        )

    def test_malformed_json_is_rejected(self):
        response = self.send_raw_request(b"{invalid-json}\n")

        self.assertFalse(response["ok"])
        self.assertEqual(
            response["error"]["code"],
            "invalid_request",
        )

    def test_incomplete_message_is_rejected(self):
        response = self.send_raw_request(
            b'{"version":1,"id":"test",'
            b'"operation":"health","params":{}}'
        )

        self.assertFalse(response["ok"])
        self.assertEqual(
            response["error"]["code"],
            "invalid_request",
        )

    def test_oversized_message_is_rejected(self):
        payload = b"x" * (MAX_MESSAGE_BYTES + 1) + b"\n"

        response = self.send_raw_request(payload)

        self.assertFalse(response["ok"])
        self.assertEqual(
            response["error"]["code"],
            "message_too_large",
        )

    def test_empty_connection_does_not_crash_service(self):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(3)
            client.connect(str(self.socket_path))
            client.shutdown(socket.SHUT_WR)

            with client.makefile("rb") as response_file:
                response = response_file.readline(MAX_MESSAGE_BYTES + 1)

        self.assertTrue(response)

        decoded = json.loads(response.decode("utf-8"))

        self.assertFalse(decoded["ok"])
        self.assertEqual(
            decoded["error"]["code"],
            "invalid_request",
        )

    def test_service_remains_available_after_invalid_request(self):
        self.send_raw_request(b"{invalid-json}\n")

        response = self.send_request({
            "version": 1,
            "id": "ipc-health-after-error",
            "operation": "health",
            "params": {},
        })

        self.assertTrue(response["ok"])
        self.assertEqual(
            response["result"]["status"],
            "healthy",
        )


if __name__ == "__main__":
    unittest.main()
