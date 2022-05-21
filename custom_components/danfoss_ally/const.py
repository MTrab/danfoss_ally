"""Danfoss_ally consts."""
from homeassistant.components.climate.const import (
    HVAC_MODE_AUTO,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
)

THERMOSTAT_MODE_AUTO = "hot"
THERMOSTAT_MODE_MANUAL = "manual"
THERMOSTAT_MODE_OFF = "pause"

HVAC_MODE_MANUAL = "manual"

PRESET_MANUAL = "Manual"
PRESET_PAUSE = "Pause"
PRESET_HOLIDAY = "Holiday"

HA_TO_DANFOSS_HVAC_MODE_MAP = {
    HVAC_MODE_OFF: THERMOSTAT_MODE_OFF,
    HVAC_MODE_HEAT: THERMOSTAT_MODE_MANUAL,
    HVAC_MODE_AUTO: THERMOSTAT_MODE_AUTO,
}

DANFOSS_TO_HA_HVAC_MODE_MAP = {
    value: key for key, value in HA_TO_DANFOSS_HVAC_MODE_MAP.items()
}

CONF_KEY = "key"
CONF_SECRET = "secret"
DATA = "data"
DEFAULT_NAME = "Danfoss"
DOMAIN = "danfoss_ally"
SIGNAL_ALLY_UPDATE_RECEIVED = "ally_update_received"
UNIQUE_ID = "unique_id"
UPDATE_LISTENER = "update_listener"
UPDATE_TRACK = "update_track"

ACTION_TYPE_SET_PRESET_TEMPERATURE = "set_preset_temperature"
ATTR_SETPOINT = "setpoint"



