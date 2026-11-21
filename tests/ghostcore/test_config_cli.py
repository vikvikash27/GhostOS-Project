
import json
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from ghostcore.config_cli import inspect_configuration, main


class ConfigCLITests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "ghostos.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_missing_config_returns_valid_default(self):
        result = inspect_configuration(self.config_path)

        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["applications"], 0)
        self.assertEqual(result["privacy_rules"], 0)
        self.assertEqual(result["network_rules"], 0)

    def test_cli_returns_success_for_valid_config(self):
        with patch(
            "ghostcore.config_cli.inspect_configuration",
            return_value={
                "status": "valid",
                "schema_version": 1,
                "applications": 1,
                "privacy_rules": 2,
                "network_rules": 1,
            },
        ):
            result = main(["--config", str(self.config_path)])

        self.assertEqual(result, 0)

    def test_cli_returns_failure_for_invalid_config(self):
        self.config_path.write_text("{invalid json")

        result = main(["--config", str(self.config_path)])

        self.assertEqual(result, 1)

    def test_inspection_does_not_modify_configuration(self):
        before = inspect_configuration(self.config_path)
        after = inspect_configuration(self.config_path)

        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
