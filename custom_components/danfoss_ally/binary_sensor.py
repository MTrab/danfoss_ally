"""Support for Ally binary_sensors."""
import logging

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_CONNECTIVITY,
    DEVICE_CLASS_WINDOW,
    DEVICE_CLASS_LOCK,
    DEVICE_CLASS_TAMPER,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (
    DATA,
    DOMAIN,
    SIGNAL_ALLY_UPDATE_RECEIVED,
)
from .entity import AllyDeviceEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up the Ally binary_sensor platform."""
    _LOGGER.debug("Setting up Danfoss Ally binary_sensor entities")
    ally = hass.data[DOMAIN][entry.entry_id][DATA]
    entities = []

    for device in ally.devices:
        if 'window_open' in ally.devices[device]:
            _LOGGER.debug("Found window detector for %s", ally.devices[device]["name"])
            entities.extend(
                [
                    AllyBinarySensor(
                        ally,
                        ally.devices[device]["name"],
                        device,
                        'open window',
                        ally.devices[device]["model"]
                    )
                ]
            )
        if 'child_lock' in ally.devices[device]:
            _LOGGER.debug("Found child lock detector for %s", ally.devices[device]["name"])
            entities.extend(
                [
                    AllyBinarySensor(
                        ally,
                        ally.devices[device]["name"],
                        device,
                        'child lock',
                        ally.devices[device]["model"]
                    )
                ]
            )
        if not ally.devices[device]["isThermostat"]:
            _LOGGER.debug("Found connection sensor for %s", ally.devices[device]["name"])
            entities.extend(
                [
                    AllyBinarySensor(
                        ally,
                        ally.devices[device]["name"],
                        device,
                        'connectivity',
                        ally.devices[device]["model"]
                    )
                ]
            )
        if 'banner_ctrl' in ally.devices[device]:
            _LOGGER.debug("Found banner_ctrl detector for %s", ally.devices[device]["name"])
            entities.extend(
                [
                    AllyBinarySensor(
                        ally,
                        ally.devices[device]["name"],
                        device,
                        'banner control',
                        ally.devices[device]["model"]
                    )
                ]
            )
    


    if entities:
        async_add_entities(entities, True)


class AllyBinarySensor(AllyDeviceEntity, BinarySensorEntity):
    """Representation of an Ally binary_sensor."""

    def __init__(self, ally, name, device_id, device_type, model):
        """Initialize Ally binary_sensor."""
        self._ally = ally
        self._device = ally.devices[device_id]
        self._device_id = device_id
        self._type = device_type
        super().__init__(name, device_id, device_type, model)

        _LOGGER.debug(
            "Device_id: %s --- Device: %s",
            self._device_id,
            self._device
        )

        self._type = device_type

        self._unique_id = f"{device_type}_{device_id}_ally"

        self._state = None

        if self._type == "link":
            self._state = self._device['online']
        elif self._type == "open window":
            self._state = bool(self._device['window_open'])
        elif self._type == "child lock":
            self._state = not bool(self._device['child_lock'])
        elif self._type == "connectivity":
            self._state = bool(self._device['online'])
        elif self._type == "banner control":
            self._state = bool(self._device['banner_ctrl'])


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
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} {self._type}"

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._state

    @property
    def device_class(self):
        """Return the class of this sensor."""
        if self._type == "link":
            return DEVICE_CLASS_CONNECTIVITY
        elif self._type == "open window":
            return DEVICE_CLASS_WINDOW
        elif self._type == "child lock":
            return DEVICE_CLASS_LOCK
        elif self._type == "connectivity":
            return DEVICE_CLASS_CONNECTIVITY
        elif self._type == "banner control":
            return DEVICE_CLASS_TAMPER
        return None

    @callback
    def _async_update_callback(self):
        """Update and write state."""
        self._async_update_data()
        self.async_write_ha_state()

    @callback
    def _async_update_data(self):
        """Load data."""
        _LOGGER.debug(
            "Loading new binary_sensor data for device %s",
            self._device_id
        )
        self._device = self._ally.devices[self._device_id]

        if self._type == "link":
            self._state = self._device['online']
        elif self._type == "open window":
            self._state = bool(self._device['window_open'])
        elif self._type == "child lock":
            self._state = not bool(self._device['child_lock'])
        elif self._type == "connectivity":
            self._state = bool(self._device['online'])
        elif self._type == "banner control":
            self._state = bool(self._device['banner_ctrl'])
