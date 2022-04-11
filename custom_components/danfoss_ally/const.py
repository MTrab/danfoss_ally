"""Danfoss_ally consts."""
from homeassistant.components.climate.const import (
    HVAC_MODE_AUTO,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
)

from pydanfossally.const import (  # pylint: disable=no-name-in-module
    THERMOSTAT_MODE_AUTO,
    THERMOSTAT_MODE_MANUAL,
    THERMOSTAT_MODE_OFF,
)

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
