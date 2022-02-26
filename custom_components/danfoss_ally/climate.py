"""Support for Danfoss Ally thermostats."""
import logging

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    CURRENT_HVAC_HEAT,
    HVAC_MODE_AUTO,
    HVAC_MODE_HEAT,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_PRESET_MODE,
    PRESET_HOME,
    PRESET_AWAY,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (
    DATA,
    DOMAIN,
    SIGNAL_ALLY_UPDATE_RECEIVED,
)
from .entity import AllyDeviceEntity

# Custom preset for pause mode
PRESET_PAUSE = "pause"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up the Danfoss Ally climate platform."""

    ally = hass.data[DOMAIN][entry.entry_id][DATA]
    entities = await hass.async_add_executor_job(_generate_entities, ally)
    _LOGGER.debug(ally.devices)
    if entities:
        async_add_entities(entities, True)


def _generate_entities(ally):
    """Create all climate entities."""
    _LOGGER.debug("Setting up Danfoss Ally climate entities")
    entities = []
    for device in ally.devices:
        if ally.devices[device]["isThermostat"]:
            entity = create_climate_entity(
                ally,
                ally.devices[device]["name"],
                device
            )
            if entity:
                entities.append(entity)
    return entities


def create_climate_entity(ally, name: str, device_id: str):
    """Create a Danfoss Ally climate entity."""

    support_flags = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE
    supported_hvac_modes = [HVAC_MODE_AUTO, HVAC_MODE_HEAT]
    heat_temperatures = None
    heat_min_temp = 4.5
    heat_max_temp = 35.0
    heat_step = 0.5

    entity = AllyClimate(
        ally,
        name,
        device_id,
        heat_min_temp,
        heat_max_temp,
        heat_step,
        supported_hvac_modes,
        support_flags,
    )
    return entity


class AllyClimate(AllyDeviceEntity, ClimateEntity):
    """Representation of a Danfoss Ally climate entity."""

    def __init__(
        self,
        ally,
        name,
        device_id,
        heat_min_temp,
        heat_max_temp,
        heat_step,
        supported_hvac_modes,
        support_flags,
    ):
        """Initialize Danfoss Ally climate entity."""
        self._ally = ally
        self._device = ally.devices[device_id]
        self._device_id = device_id
        super().__init__(name, device_id, "climate")

        _LOGGER.debug(
            "Device_id: %s --- Device: %s",
            self._device_id,
            self._device
        )

        self._unique_id = f"climate_{device_id}_ally"

        self._supported_hvac_modes = supported_hvac_modes
        self._supported_preset_modes = [PRESET_HOME, PRESET_AWAY, PRESET_PAUSE]
        self._support_flags = support_flags

        self._available = False

        # Current temperature
        if 'temperature' in self._device:
            self._cur_temp = self._device['temperature']
        else:
            # TEMPORARY fix for missing temperature sensor
            self._cur_temp = self._device["setpoint"]

        # Low temperature set in Ally app
        if 'lower_temp' in self._device:
            self._heat_min_temp = self._device['lower_temp']
        else:
            self._heat_min_temp = heat_min_temp

        # High temperature set in Ally app
        if 'upper_temp' in self._device:
            self._heat_max_temp = self._device['upper_temp']
        else:
            self._heat_max_temp = heat_max_temp

        self._heat_step = heat_step
        self._target_temp = None


    async def async_added_to_hass(self):
        """Register for sensor updates."""

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_ALLY_UPDATE_RECEIVED,
                self._async_update_callback,
            )
        )

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._support_flags

    @property
    def name(self):
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id

    @property
    def current_temperature(self):
        """Return the sensor temperature."""
        #return self._cur_temp
        if 'temperature' in self._device:
            return self._device['temperature']
        else:
            # TEMPORARY fix for missing temperature sensor
            return self._device["setpoint"]

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.
        Need to be one of HVAC_MODE_*.
        """
        if 'mode' in self._device:
            if self._device['mode'] == 'at_home' or self._device['mode'] == 'leaving_home':
                return HVAC_MODE_AUTO
            elif self._device['mode'] == 'manual':
                return HVAC_MODE_HEAT

    @property
    def preset_mode(self):
        """The current active preset.
        """
        if 'mode' in self._device:
            if self._device['mode'] == 'at_home':
                return PRESET_HOME
            elif self._device['mode'] == 'leaving_home':
                return PRESET_AWAY
            elif self._device['mode'] == 'pause':
                return PRESET_PAUSE

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.
        Need to be a subset of HVAC_MODES.
        """
        return self._supported_hvac_modes

    @property
    def preset_modes(self):
        """Return the list of available preset modes.
        """
        return self._supported_preset_modes

    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported.
        Need to be one of CURRENT_HVAC_*.
        """
        return CURRENT_HVAC_HEAT

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return TEMP_CELSIUS

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return self._heat_step

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._device["setpoint"]

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        self._ally.setTemperature(self._device_id, temperature)

    @property
    def available(self):
        """Return if the device is available."""
        return self._device["online"]

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._heat_min_temp

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._heat_max_temp

    @callback
    def _async_update_data(self):
        """Load data."""
        _LOGGER.debug(
            "Loading new climate data for device %s",
            self._device_id
        )
        self._device = self._ally.devices[self._device_id]

    @callback
    def _async_update_callback(self):
        """Load data and update state."""
        self._async_update_data()
        self.async_write_ha_state()

    def set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        #Currently unsupported by API