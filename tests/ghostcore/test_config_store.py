
import os
import tempfile
import unittest
from pathlib import Path

from ghostcore.config_store import (
    ConfigError,
    DEFAULT_CONFIG,
    GhostConfigStore,
)


class GhostConfigStoreTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp_dir.name)
        os.chmod(self.directory, 0o700)
        self.path = self.directory / "config.json"
        self.store = GhostConfigStore(self.path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def valid_config(self):
        return {
            "schema_version": 1,
            "applications": [
                {"application_id": "ghost.browser", "uid": os.getuid()}
            ],
            "privacy_rules": [
                {
                    "uid": os.getuid(),
                    "capability": "CAMERA",
                    "decision": "DENY",
                }
            ],
            "network_rules": [
                {
                    "uid": os.getuid(),
                    "capability": "INTERNET",
                    "decision": "DENY",
                    "destination_cidr": None,
                }
            ],
        }

    def test_missing_file_returns_default_config(self):
        self.assertEqual(self.store.load(), DEFAULT_CONFIG)

    def test_save_and_load_configuration(self):
        config = self.valid_config()
        self.store.save(config)
        self.assertEqual(self.store.load(), config)

    def test_saved_file_has_private_permissions(self):
        self.store.save(self.valid_config())
        self.assertEqual(
            self.path.stat().st_mode & 0o777,
            0o600,
        )

    def test_duplicate_uid_is_rejected(self):
        config = self.valid_config()
        config["applications"].append({
            "application_id": "ghost.vault",
            "uid": os.getuid(),
        })

        with self.assertRaises(ConfigError):
            self.store.save(config)

    def test_unknown_application_uid_is_rejected(self):
        config = self.valid_config()
        config["privacy_rules"][0]["uid"] = os.getuid() + 1000

        with self.assertRaises(ConfigError):
            self.store.save(config)

    def test_invalid_capability_is_rejected(self):
        config = self.valid_config()
        config["privacy_rules"][0]["capability"] = "ROOT_ACCESS"

        with self.assertRaises(ConfigError):
            self.store.save(config)

    def test_invalid_network_cidr_is_rejected(self):
        config = self.valid_config()
        config["network_rules"][0]["destination_cidr"] = "not-a-network"

        with self.assertRaises(ConfigError):
            self.store.save(config)

    def test_boolean_uid_is_rejected(self):
        config = self.valid_config()
        config["applications"][0]["uid"] = True

        with self.assertRaises(ConfigError):
            self.store.save(config)

    def test_unknown_configuration_field_is_rejected(self):
        config = self.valid_config()
        config["unexpected"] = "value"

        with self.assertRaises(ConfigError):
            self.store.save(config)

    def test_corrupt_json_is_rejected(self):
        self.path.write_text("{invalid json", encoding="utf-8")
        os.chmod(self.path, 0o600)

        with self.assertRaises(ConfigError):
            self.store.load()

    def test_symlink_configuration_is_rejected(self):
        target = self.directory / "target.json"
        target.write_text("{}", encoding="utf-8")
        os.chmod(target, 0o600)

        self.path.symlink_to(target)

        with self.assertRaises(ConfigError):
            self.store.load()


if __name__ == "__main__":
    unittest.main()
