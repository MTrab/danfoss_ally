"""Constants for the Danfoss Ally integration."""

from __future__ import annotations

from datetime import timedelta
import json
from pathlib import Path

from homeassistant.const import Platform

CONF_KEY = "key"
CONF_SECRET = "secret"
CONF_EXTERNAL_SENSORS = "external_sensors"
CONF_WINDOW_SENSORS = "window_sensors"
CONF_ENTITY_ID = "entity_id"

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

# The API reports -80.0 when no external temperature is set. Thermostats that
# never had an external sensor can also report the Zigbee invalid marker
# (0x8000 = -327.68). Anything at or below this value is not a reading.
EXTERNAL_TEMPERATURE_DISABLED = -80.0

PRESET_PAUSE = "pause"
PRESET_HOLIDAY = "holiday"

ACTION_TYPE_SET_PRESET_TEMPERATURE = "set_preset_temperature"


def _load_integration_version() -> str:
    """Read the integration version from the manifest for outbound identifiers."""
    manifest_path = Path(__file__).with_name("manifest.json")
    try:
        with manifest_path.open(encoding="utf-8") as manifest_file:
            return str(json.load(manifest_file)["version"])
    except (OSError, KeyError, TypeError, ValueError):
        return "unknown"


def is_valid_external_temperature(value: object) -> bool:
    """Return whether an external sensor value is a real temperature reading."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return value > EXTERNAL_TEMPERATURE_DISABLED


INTEGRATION_VERSION = _load_integration_version()
USER_AGENT_PREFIX = f"Home-Assistant-Danfoss-Ally-{INTEGRATION_VERSION}"
