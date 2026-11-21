
import argparse
import json
import sys
from pathlib import Path

from .config_store import GhostConfigStore, ConfigError


def default_config_path():
    return (
        Path.home()
        / ".local"
        / "state"
        / "ghostos"
        / "config"
        / "ghostos.json"
    )


def inspect_configuration(config_path):
    store = GhostConfigStore(config_path)
    config = store.load()

    return {
        "status": "valid",
        "schema_version": config["schema_version"],
        "applications": len(config["applications"]),
        "privacy_rules": len(config["privacy_rules"]),
        "network_rules": len(config["network_rules"]),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate and inspect GhostOS configuration."
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=default_config_path(),
        help="Path to the GhostOS configuration file.",
    )

    args = parser.parse_args(argv)
    config_path = args.config.expanduser()

    if not config_path.is_absolute():
        config_path = Path.cwd() / config_path

    try:
        result = inspect_configuration(config_path)
    except (ConfigError, OSError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "status": "invalid",
                    "error": str(exc),
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
