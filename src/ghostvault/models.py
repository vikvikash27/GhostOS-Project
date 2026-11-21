
"""GhostVault state and error definitions."""

from enum import Enum


class VaultState(str, Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"


class VaultError(Exception):
    """Base exception for GhostVault."""


class VaultAlreadyExistsError(VaultError):
    pass


class VaultNotFoundError(VaultError):
    pass


class VaultLockedError(VaultError):
    pass


class VaultAuthenticationError(VaultError):
    pass


class InvalidKeyError(VaultError):
    pass
