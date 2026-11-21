
import unittest

from ghostvault.models import VaultState


class VaultModelTests(unittest.TestCase):

    def test_initial_state_is_locked(self):
        self.assertEqual(VaultState.LOCKED.value, "locked")

    def test_unlocked_state(self):
        self.assertEqual(VaultState.UNLOCKED.value, "unlocked")


if __name__ == "__main__":
    unittest.main()
