
import unittest

from ghostcore.identity import (
    ApplicationIdentity,
    ApplicationRegistry,
    ProcessIdentity,
)


class ProcessIdentityTests(unittest.TestCase):

    def test_valid_identity(self):
        identity = ProcessIdentity(pid=1234, uid=1000, gid=1000)

        self.assertEqual(identity.uid, 1000)

    def test_invalid_pid(self):
        with self.assertRaises(ValueError):
            ProcessIdentity(pid=0, uid=1000, gid=1000)

    def test_invalid_uid(self):
        with self.assertRaises(ValueError):
            ProcessIdentity(pid=1234, uid=-1, gid=1000)

    def test_boolean_uid_is_rejected(self):
        with self.assertRaises(ValueError):
            ProcessIdentity(pid=1234, uid=True, gid=1000)


class ApplicationRegistryTests(unittest.TestCase):

    def setUp(self):
        self.registry = ApplicationRegistry()

    def test_register_and_resolve(self):
        application = ApplicationIdentity(
            application_id="com.ghostos.browser",
            uid=1000,
        )

        self.registry.register(application)

        resolved = self.registry.resolve(
            ProcessIdentity(pid=1234, uid=1000, gid=1000)
        )

        self.assertEqual(resolved.application_id, "com.ghostos.browser")

    def test_unknown_uid_is_unregistered(self):
        identity = ProcessIdentity(pid=1234, uid=1001, gid=1001)

        self.assertIsNone(self.registry.resolve(identity))

    def test_duplicate_uid_is_rejected(self):
        self.registry.register(
            ApplicationIdentity("com.ghostos.browser", 1000)
        )

        with self.assertRaises(ValueError):
            self.registry.register(
                ApplicationIdentity("com.ghostos.vault", 1000)
            )

    def test_empty_application_id_is_rejected(self):
        with self.assertRaises(ValueError):
            self.registry.register(ApplicationIdentity("", 1000))


if __name__ == "__main__":
    unittest.main()
