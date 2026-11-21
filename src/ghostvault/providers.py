
"""Key-provider contracts and test-only provider."""

from __future__ import annotations

from typing import Protocol


class KeyProvider(Protocol):
    """Contract for an external key-management implementation."""

    def create_key(self, vault_id: str) -> bytes:
        """Create and securely retain a new key."""
        ...

    def load_key(self, vault_id: str) -> bytes:
        """Retrieve an existing key."""
        ...

    def delete_key(self, vault_id: str) -> None:
        """Delete a retained key, subject to provider guarantees."""
        ...


class InMemoryTestKeyProvider:
    """
    Test-only key provider.

    Keys exist only in process memory. This is NOT suitable for
    production storage or persistent vaults.
    """

    def __init__(self) -> None:
        self._keys: dict[str, bytes] = {}

    def create_key(self, vault_id: str) -> bytes:
        import secrets

        if vault_id in self._keys:
            raise ValueError("A key already exists for this vault")

        key = secrets.token_bytes(32)
        self._keys[vault_id] = key
        return key

    def load_key(self, vault_id: str) -> bytes:
        try:
            return self._keys[vault_id]
        except KeyError as exc:
            raise KeyError("Vault key not found") from exc

    def delete_key(self, vault_id: str) -> None:
        self._keys.pop(vault_id, None)
