"""Constants for the Danfoss Ally integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

CONF_KEY = "key"
CONF_SECRET = "secret"

DEFAULT_NAME = "Danfoss"
DOMAIN = "danfoss_ally"
API_TIMEOUT = 10.0
SCAN_INTERVAL = timedelta(seconds=45)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
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
