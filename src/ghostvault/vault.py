
"""AES-256-GCM encrypted vault storage."""

from __future__ import annotations

import os
import re
import secrets
import stat
import tempfile
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .models import (
    InvalidKeyError,
    VaultAlreadyExistsError,
    VaultAuthenticationError,
    VaultError,
    VaultLockedError,
    VaultNotFoundError,
    VaultState,
)
from .providers import KeyProvider


MAGIC = b"GOSV1"
FORMAT_VERSION = 1
NONCE_SIZE = 12
KEY_SIZE = 32
TAG_SIZE = 16
MAX_PLAINTEXT_SIZE = 16 * 1024 * 1024


class GhostVault:
    """Encrypted file-backed vault with an injected key provider."""

    def __init__(
        self,
        vault_id: str,
        path: Path,
        key_provider: KeyProvider,
    ) -> None:
        if not isinstance(vault_id, str) or not re.fullmatch(
            r"[a-zA-Z0-9_-]{1,64}", vault_id
        ):
            raise ValueError("Invalid vault ID")

        self.vault_id = vault_id
        self.path = Path(path)
        self.key_provider = key_provider
        self._key: bytes | None = None
        self.state = VaultState.LOCKED

    def _aad(self) -> bytes:
        return f"GhostVault:{FORMAT_VERSION}:{self.vault_id}".encode("utf-8")

    def _validate_key(self, key: bytes) -> bytes:
        if not isinstance(key, bytes) or len(key) != KEY_SIZE:
            raise InvalidKeyError("Provider must return a 32-byte AES-256 key")
        return key

    def _validate_parent(self) -> None:
        parent = self.path.parent

        if not parent.exists():
            parent.mkdir(parents=True, mode=0o700)

        info = parent.stat()

        if not stat.S_ISDIR(info.st_mode):
            raise VaultError("Vault parent is not a directory")

        if info.st_uid != os.getuid():
            raise VaultError("Vault directory has the wrong owner")

        if stat.S_IMODE(info.st_mode) & 0o077:
            raise VaultError("Vault directory must be private")

    def _validate_existing_file(self) -> None:
        try:
            info = self.path.lstat()
        except FileNotFoundError as exc:
            raise VaultNotFoundError("Vault file does not exist") from exc

        if not stat.S_ISREG(info.st_mode):
            raise VaultError("Vault path must be a regular file")

        if info.st_uid != os.getuid():
            raise VaultError("Vault file has the wrong owner")

        if stat.S_IMODE(info.st_mode) & 0o077:
            raise VaultError("Vault file must be private")

    def _write_encrypted(self, payload: bytes) -> None:
        self._validate_parent()

        if len(payload) > MAX_PLAINTEXT_SIZE:
            raise VaultError("Vault data exceeds the size limit")

        if self.path.is_symlink():
            raise VaultError("Refusing to replace a symbolic link")

        nonce = secrets.token_bytes(NONCE_SIZE)
        ciphertext = AESGCM(self._require_key()).encrypt(
            nonce,
            payload,
            self._aad(),
        )

        blob = MAGIC + bytes([FORMAT_VERSION]) + nonce + ciphertext

        fd, temporary_name = tempfile.mkstemp(
            prefix=".ghostvault-",
            dir=self.path.parent,
        )
        temporary_path = Path(temporary_name)

        try:
            os.fchmod(fd, 0o600)

            with os.fdopen(fd, "wb") as file:
                file.write(blob)
                file.flush()
                os.fsync(file.fileno())

            os.replace(temporary_path, self.path)

            directory_fd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)

        except Exception:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
            raise

    def _read_encrypted(self) -> bytes:
        self._validate_existing_file()

        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        flags |= getattr(os, "O_CLOEXEC", 0)

        fd = os.open(self.path, flags)

        try:
            info = os.fstat(fd)

            if not stat.S_ISREG(info.st_mode):
                raise VaultError("Vault target is not a regular file")

            if info.st_uid != os.getuid():
                raise VaultError("Vault target has the wrong owner")

            if stat.S_IMODE(info.st_mode) & 0o077:
                raise VaultError("Vault target must be private")

            with os.fdopen(fd, "rb") as file:
                fd = -1
                blob = file.read(
                    MAX_PLAINTEXT_SIZE + len(MAGIC) + 1
                    + NONCE_SIZE + TAG_SIZE + 1
                )

        finally:
            if fd >= 0:
                os.close(fd)

        minimum_size = len(MAGIC) + 1 + NONCE_SIZE + TAG_SIZE

        if len(blob) < minimum_size or len(blob) > (
            MAX_PLAINTEXT_SIZE + len(MAGIC) + 1 + NONCE_SIZE + TAG_SIZE
        ):
            raise VaultError("Invalid vault file size")

        if blob[:len(MAGIC)] != MAGIC:
            raise VaultError("Invalid vault file header")

        if blob[len(MAGIC)] != FORMAT_VERSION:
            raise VaultError("Unsupported vault format version")

        nonce_start = len(MAGIC) + 1
        nonce = blob[nonce_start:nonce_start + NONCE_SIZE]
        ciphertext = blob[nonce_start + NONCE_SIZE:]

        try:
            return AESGCM(self._require_key()).decrypt(
                nonce,
                ciphertext,
                self._aad(),
            )
        except InvalidTag as exc:
            raise VaultAuthenticationError(
                "Vault authentication failed"
            ) from exc

    def _require_key(self) -> bytes:
        if self._key is None or self.state != VaultState.UNLOCKED:
            raise VaultLockedError("Vault is locked")
        return self._key

    def create(self) -> None:
        if self.path.exists() or self.path.is_symlink():
            raise VaultAlreadyExistsError("Vault file already exists")

        self._validate_parent()

        key = self._validate_key(
            self.key_provider.create_key(self.vault_id)
        )

        self._key = key
        self.state = VaultState.UNLOCKED

        try:
            self._write_encrypted(b"")
        except Exception:
            self.lock()
            # Key deletion is deliberately not automatic: provider
            # deletion guarantees and recovery semantics vary.
            raise

    def unlock(self) -> None:
        if self.state == VaultState.UNLOCKED:
            return

        key = self._validate_key(
            self.key_provider.load_key(self.vault_id)
        )

        self._key = key
        self.state = VaultState.UNLOCKED

        try:
            self._read_encrypted()
        except Exception:
            self.lock()
            raise

    def lock(self) -> None:
        # Python cannot guarantee secure zeroization of immutable bytes.
        # This drops our reference; production key handling needs a
        # platform-backed provider and stronger memory protections.
        self._key = None
        self.state = VaultState.LOCKED

    def read(self) -> bytes:
        return self._read_encrypted()

    def write(self, payload: bytes) -> None:
        if not isinstance(payload, bytes):
            raise TypeError("Vault payload must be bytes")

        self._require_key()
        self._write_encrypted(payload)

    def delete_key(self) -> None:
        self.lock()
        self.key_provider.delete_key(self.vault_id)
