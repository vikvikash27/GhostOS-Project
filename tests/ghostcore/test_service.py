
import unittest

from ghostcore.protocol import ProtocolError
from ghostcore.service import GhostCore


class GhostCoreTests(unittest.TestCase):
    def setUp(self):
        self.core = GhostCore()

    def test_health_operation(self):
        result = self.core.dispatch("health", {})

        self.assertEqual(result["service"], "ghostcore")
        self.assertEqual(result["status"], "healthy")
        self.assertFalse(result["privileged"])
        self.assertGreaterEqual(result["uptime_seconds"], 0)

    def test_health_rejects_parameters(self):
        with self.assertRaises(ProtocolError):
            self.core.dispatch("health", {"unexpected": True})

    def test_unknown_operation_is_rejected(self):
        with self.assertRaises(ProtocolError):
            self.core.dispatch("execute_command", {})


if __name__ == "__main__":
    unittest.main()
