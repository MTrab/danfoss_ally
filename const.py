from homeassistant.components.climate.const import (
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_DRY,
    CURRENT_HVAC_FAN,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_OFF,
    HVAC_MODE_AUTO,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    PRESET_AWAY,
    PRESET_HOME,
)

CONF_KEY = "key"
CONF_SECRET = "secret"
DATA = "data"
DEFAULT_NAME = "Danfoss"
DOMAIN = "danfoss_ally"
SIGNAL_ALLY_UPDATE_RECEIVED = "ally_update_received"
SUPPORT_PRESET = [PRESET_AWAY, PRESET_HOME]
UNIQUE_ID = "unique_id"
UPDATE_LISTENER = "update_listener"
UPDATE_TRACK = "update_track"