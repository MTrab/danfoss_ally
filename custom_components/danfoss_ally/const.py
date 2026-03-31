"""Constants for the Danfoss Ally integration."""

from __future__ import annotations

from datetime import timedelta
import json
from pathlib import Path

from homeassistant.const import Platform

CONF_KEY = "key"
CONF_SECRET = "secret"

DEFAULT_NAME = "Danfoss"
DOMAIN = "danfoss_ally"
API_TIMEOUT = 30.0
SCAN_INTERVAL = timedelta(seconds=60)
REFRESH_DEVICE_CONCURRENCY = 5
REFRESH_DEVICE_MIN_INTERVAL = 0.10
DEVICE_DISCOVERY_INTERVAL = 600.0
DEGRADED_REFRESH_COOLDOWN = 600.0
HOT_REFRESH_TIMEOUT = 300.0

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
]

PRESET_MANUAL = "manual"
PRESET_PAUSE = "pause"
PRESET_HOLIDAY_AWAY = "holiday_away"
PRESET_HOLIDAY_HOME = "holiday_home"

LEGACY_PRESET_ALIASES = {
    "holiday": PRESET_HOLIDAY_AWAY,
    "holiday_sat": PRESET_HOLIDAY_HOME,
}

ACTION_TYPE_SET_PRESET_TEMPERATURE = "set_preset_temperature"


def _load_integration_version() -> str:
    """Read the integration version from the manifest for outbound identifiers."""
    manifest_path = Path(__file__).with_name("manifest.json")
    try:
        with manifest_path.open(encoding="utf-8") as manifest_file:
            return str(json.load(manifest_file)["version"])
    except OSError, KeyError, TypeError, ValueError:
        return "unknown"


INTEGRATION_VERSION = _load_integration_version()
USER_AGENT_PREFIX = f"Home-Assistant-Danfoss-Ally-{INTEGRATION_VERSION}"
