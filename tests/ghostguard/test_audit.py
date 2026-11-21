
import json
import os
import tempfile
import unittest
from pathlib import Path

from ghostguard.audit import AuditLogger
from ghostguard.models import EventDecision, SecurityEvent


class SecurityEventTests(unittest.TestCase):

    def test_event_creation(self):
        event = SecurityEvent.create(
            source="ghostprivacy",
            event_type="permission_check",
            decision=EventDecision.DENY,
            subject_uid=1000,
            reason="no_matching_policy",
        )

        self.assertEqual(event.source, "ghostprivacy")
        self.assertEqual(event.decision, EventDecision.DENY)
        self.assertEqual(event.subject_uid, 1000)

    def test_invalid_source_is_rejected(self):
        with self.assertRaises(ValueError):
            SecurityEvent.create(
                source="../malicious",
                event_type="test",
                decision=EventDecision.INFO,
            )

    def test_invalid_uid_is_rejected(self):
        with self.assertRaises(ValueError):
            SecurityEvent.create(
                source="ghostcore",
                event_type="test",
                decision=EventDecision.INFO,
                subject_uid=-1,
            )

    def test_oversized_reason_is_rejected(self):
        with self.assertRaises(ValueError):
            SecurityEvent.create(
                source="ghostcore",
                event_type="test",
                decision=EventDecision.INFO,
                reason="x" * 257,
            )


class AuditLoggerTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.directory = Path(self.temp_dir.name)
        os.chmod(self.directory, 0o700)

        self.log_path = self.directory / "events.jsonl"
        self.logger = AuditLogger(self.log_path)

    def make_event(self):
        return SecurityEvent.create(
            source="ghostprivacy",
            event_type="permission_check",
            decision=EventDecision.DENY,
            subject_uid=1000,
            reason="no_matching_policy",
        )

    def test_event_is_written(self):
        event = self.make_event()
        self.logger.record(event)

        content = self.log_path.read_text()
        stored = json.loads(content)

        self.assertEqual(stored["event_id"], event.event_id)
        self.assertEqual(stored["decision"], "deny")

    def test_multiple_events_are_appended(self):
        self.logger.record(self.make_event())
        self.logger.record(self.make_event())

        lines = self.log_path.read_text().splitlines()

        self.assertEqual(len(lines), 2)

    def test_log_file_has_private_permissions(self):
        self.logger.record(self.make_event())

        mode = self.log_path.stat().st_mode & 0o777

        self.assertEqual(mode, 0o600)

    def test_symlink_target_is_rejected(self):
        target = self.directory / "target.txt"
        target.write_text("protected")

        link = self.directory / "link.jsonl"
        link.symlink_to(target)

        with self.assertRaises(PermissionError):
            AuditLogger(link)


if __name__ == "__main__":
    unittest.main()
