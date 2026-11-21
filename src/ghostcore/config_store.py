
"""Secure, versioned persistence for GhostOS security configuration."""

import copy
import ipaddress
import json
import os
import re
import stat
import tempfile
from pathlib import Path


SCHEMA_VERSION = 1

DEFAULT_CONFIG = {
    "schema_version": SCHEMA_VERSION,
    "applications": [],
    "privacy_rules": [],
    "network_rules": [],
}

APP_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")

PRIVACY_CAPABILITIES = {
    "CAMERA",
    "MICROPHONE",
    "LOCATION",
    "FILE_READ",
    "FILE_WRITE",
    "NETWORK",
}

NETWORK_CAPABILITIES = {
    "INTERNET",
    "LOCAL_NETWORK",
    "DNS",
}

DECISIONS = {"ALLOW", "DENY"}


class ConfigError(Exception):
    """Raised when configuration is invalid or unsafe."""


def _validate_uid(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ConfigError("UID must be a non-negative integer")


def validate_config(config):
    if not isinstance(config, dict):
        raise ConfigError("Configuration must be an object")

    expected = {
        "schema_version",
        "applications",
        "privacy_rules",
        "network_rules",
    }

    if set(config) != expected:
        raise ConfigError("Unexpected or missing configuration fields")

    if config["schema_version"] != SCHEMA_VERSION:
        raise ConfigError("Unsupported configuration schema version")

    applications = config["applications"]
    privacy_rules = config["privacy_rules"]
    network_rules = config["network_rules"]

    if not all(isinstance(x, list) for x in (
        applications, privacy_rules, network_rules
    )):
        raise ConfigError("Configuration collections must be lists")

    registered_uids = set()
    application_ids = set()

    for app in applications:
        if not isinstance(app, dict) or set(app) != {"application_id", "uid"}:
            raise ConfigError("Invalid application entry")

        app_id = app["application_id"]
        uid = app["uid"]

        if not isinstance(app_id, str) or not APP_ID_PATTERN.fullmatch(app_id):
            raise ConfigError("Invalid application ID")

        _validate_uid(uid)

        if app_id in application_ids or uid in registered_uids:
            raise ConfigError("Duplicate application ID or UID")

        application_ids.add(app_id)
        registered_uids.add(uid)

    seen_privacy = set()

    for rule in privacy_rules:
        if not isinstance(rule, dict) or set(rule) != {
            "uid", "capability", "decision"
        }:
            raise ConfigError("Invalid privacy rule")

        uid = rule["uid"]
        _validate_uid(uid)

        if uid not in registered_uids:
            raise ConfigError("Privacy rule references an unknown UID")

        if rule["capability"] not in PRIVACY_CAPABILITIES:
            raise ConfigError("Unknown privacy capability")

        if rule["decision"] not in DECISIONS:
            raise ConfigError("Invalid privacy decision")

        key = (uid, rule["capability"])
        if key in seen_privacy:
            raise ConfigError("Duplicate privacy rule")
        seen_privacy.add(key)

    seen_network = set()

    for rule in network_rules:
        if not isinstance(rule, dict) or set(rule) != {
            "uid", "capability", "decision", "destination_cidr"
        }:
            raise ConfigError("Invalid network rule")

        uid = rule["uid"]
        _validate_uid(uid)

        if uid not in registered_uids:
            raise ConfigError("Network rule references an unknown UID")

        if rule["capability"] not in NETWORK_CAPABILITIES:
            raise ConfigError("Unknown network capability")

        if rule["decision"] not in DECISIONS:
            raise ConfigError("Invalid network decision")

        destination = rule["destination_cidr"]

        if destination is not None:
            if not isinstance(destination, str):
                raise ConfigError("Destination CIDR must be a string or null")
            try:
                ipaddress.ip_network(destination, strict=False)
            except ValueError as exc:
                raise ConfigError("Invalid destination CIDR") from exc

        key = (uid, rule["capability"], destination)
        if key in seen_network:
            raise ConfigError("Duplicate network rule")
        seen_network.add(key)

    return copy.deepcopy(config)


class GhostConfigStore:
    """Owner-only JSON configuration storage with atomic replacement."""

    def __init__(self, path):
        self.path = Path(path)

        if not self.path.is_absolute():
            raise ConfigError("Configuration path must be absolute")

        self.directory = self.path.parent
        self._ensure_directory()

    def _ensure_directory(self):
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)

        info = os.lstat(self.directory)

        if not stat.S_ISDIR(info.st_mode):
            raise ConfigError("Configuration parent is not a directory")

        if info.st_uid != os.getuid():
            raise ConfigError("Configuration directory has the wrong owner")

        if info.st_mode & 0o077:
            raise ConfigError("Configuration directory permissions are too broad")

    def load(self):
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)

        try:
            fd = os.open(self.path, flags)
        except FileNotFoundError:
            return copy.deepcopy(DEFAULT_CONFIG)
        except OSError as exc:
            raise ConfigError("Cannot safely open configuration file") from exc

        try:
            info = os.fstat(fd)

            if not stat.S_ISREG(info.st_mode):
                raise ConfigError("Configuration path is not a regular file")

            if info.st_uid != os.getuid():
                raise ConfigError("Configuration file has the wrong owner")

            if info.st_mode & 0o077:
                raise ConfigError("Configuration file permissions are too broad")

            if info.st_size > 1024 * 1024:
                raise ConfigError("Configuration file is too large")

            with os.fdopen(fd, "r", encoding="utf-8") as handle:
                fd = -1
                data = json.load(handle)

            return validate_config(data)

        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ConfigError("Configuration file is not valid JSON") from exc
        finally:
            if fd >= 0:
                os.close(fd)

    def save(self, config):
        validated = validate_config(config)
        self._ensure_directory()

        fd, temporary_path = tempfile.mkstemp(
            prefix=".ghostos-config-",
            suffix=".tmp",
            dir=self.directory,
        )

        try:
            os.fchmod(fd, 0o600)

            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                fd = -1
                json.dump(
                    validated,
                    handle,
                    indent=2,
                    sort_keys=True,
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())

            os.replace(temporary_path, self.path)

            directory_fd = os.open(
                self.directory,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
            )
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)

        except Exception:
            if fd >= 0:
                os.close(fd)
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
            raise
