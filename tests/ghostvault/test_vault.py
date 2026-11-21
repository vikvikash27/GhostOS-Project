
import os
import tempfile
import unittest
from pathlib import Path

from ghostvault.models import (
    VaultAuthenticationError,
    VaultLockedError,
    VaultState,
)
from ghostvault.providers import InMemoryTestKeyProvider
from ghostvault.vault import GhostVault


class GhostVaultTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.directory = Path(self.temp.name)
        os.chmod(self.directory, 0o700)

        self.provider = InMemoryTestKeyProvider()
        self.path = self.directory / "personal.vault"

        self.vault = GhostVault(
            vault_id="personal",
            path=self.path,
            key_provider=self.provider,
        )

    def test_create_vault(self):
        self.vault.create()

        self.assertTrue(self.path.exists())
        self.assertEqual(self.vault.state, VaultState.UNLOCKED)

    def test_new_vault_is_empty(self):
        self.vault.create()

        self.assertEqual(self.vault.read(), b"")

    def test_write_and_read(self):
        self.vault.create()
        content = b"GhostOS private test data"

        self.vault.write(content)

        self.assertEqual(self.vault.read(), content)

    def test_lock_prevents_read(self):
        self.vault.create()
        self.vault.lock()

        self.assertEqual(self.vault.state, VaultState.LOCKED)

        with self.assertRaises(VaultLockedError):
            self.vault.read()

    def test_lock_prevents_write(self):
        self.vault.create()
        self.vault.lock()

        with self.assertRaises(VaultLockedError):
            self.vault.write(b"blocked")

    def test_unlock_restores_access(self):
        self.vault.create()
        self.vault.write(b"persistent test data")
        self.vault.lock()
        self.vault.unlock()

        self.assertEqual(self.vault.read(), b"persistent test data")

    def test_wrong_key_fails_authentication(self):
        self.vault.create()
        self.vault.write(b"protected data")
        self.vault.lock()

        # Replace the test key with a different key.
        self.provider._keys["personal"] = b"x" * 32

        with self.assertRaises(VaultAuthenticationError):
            self.vault.unlock()

        self.assertEqual(self.vault.state, VaultState.LOCKED)

    def test_tampered_ciphertext_fails_authentication(self):
        self.vault.create()
        self.vault.write(b"protected data")
        self.vault.lock()

        blob = bytearray(self.path.read_bytes())
        blob[-1] ^= 0x01
        self.path.write_bytes(blob)
        os.chmod(self.path, 0o600)

        with self.assertRaises(VaultAuthenticationError):
            self.vault.unlock()

        self.assertEqual(self.vault.state, VaultState.LOCKED)

    def test_vault_file_is_private(self):
        self.vault.create()

        mode = self.path.stat().st_mode & 0o777

        self.assertEqual(mode, 0o600)

    def test_duplicate_creation_is_rejected(self):
        self.vault.create()

        from ghostvault.models import VaultAlreadyExistsError

        with self.assertRaises(VaultAlreadyExistsError):
            self.vault.create()

    def test_invalid_vault_id_is_rejected(self):
        with self.assertRaises(ValueError):
            GhostVault(
                vault_id="../unsafe",
                path=self.path,
                key_provider=self.provider,
            )

    def test_non_bytes_payload_is_rejected(self):
        self.vault.create()

        with self.assertRaises(TypeError):
            self.vault.write("not bytes")

    def test_oversized_payload_is_rejected(self):
        self.vault.create()

        with self.assertRaises(Exception):
            self.vault.write(b"x" * (16 * 1024 * 1024 + 1))


if __name__ == "__main__":
    unittest.main()
