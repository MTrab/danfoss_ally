"""Support for Ally sensors."""
from __future__ import annotations

from enum import IntEnum
import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorEntityDescription,
    SensorDeviceClass,
)
from homeassistant.const import (
    PERCENTAGE,
    TEMP_CELSIUS,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from pydanfossally import DanfossAlly


from .const import (
    DATA,
    DOMAIN,
    SIGNAL_ALLY_UPDATE_RECEIVED,
)
from .entity import AllyDeviceEntity

_LOGGER = logging.getLogger(__name__)


class AllySensorType(IntEnum):
    """Supported sensor types."""

    TEMPERATURE = 0
    BATTERY = 1
    HUMIDITY = 2


SENSORS = [
    SensorEntityDescription(
        key=AllySensorType.TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=None,
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        name="{} Temperature",
    ),
    SensorEntityDescription(
        key=AllySensorType.BATTERY,
        device_class=SensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        name="{} Battery",
    ),
    SensorEntityDescription(
        key=AllySensorType.HUMIDITY,
        device_class=SensorDeviceClass.HUMIDITY,
        entity_category=None,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        name="{} Humidity",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up the Ally binary_sensor platform."""
    _LOGGER.debug("Setting up Danfoss Ally sensor entities")
    ally = hass.data[DOMAIN][entry.entry_id][DATA]
    entities = []

    for device in ally.devices:
        for sensor in SENSORS:
            sensor_type = AllySensorType(sensor.key).name
            if sensor_type in ally.devices[device]:
                _LOGGER.debug(
                    "Found %s sensor for %s", sensor_type, ally.devices[device]["name"]
                )
                entities.extend(
                    [AllySensor(ally, ally.devices[device]["name"], device, sensor)]
                )

    if entities:
        async_add_entities(entities, True)


class AllySensor(AllyDeviceEntity, SensorEntity):
    """Representation of an Ally sensor."""

    def __init__(
        self, ally: DanfossAlly, name, device_id, description: SensorEntityDescription
    ):
        """Initialize Ally binary_sensor."""
        self.entity_description = description
        self._ally = ally
        self._device = ally.devices[device_id]
        self._device_id = device_id
        self._type = AllySensorType(description.key).name
        super().__init__(name, device_id, self._type)

        _LOGGER.debug("Device_id: %s --- Device: %s", self._device_id, self._device)

        self._attr_native_value = None
        self._attr_extra_state_attributes = None
        self._attr_name = self.entity_description.name.format(name)
        self._attr_unique_id = f"{self._type}_{device_id}_ally"

    async def async_added_to_hass(self):
        """Register for sensor updates."""

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_ALLY_UPDATE_RECEIVED,
                self._async_update_callback,
            )
        )

    @callback
    def _async_update_callback(self):
        """Update and write state."""
        self._async_update_data()
        self.async_write_ha_state()

    @callback
    def _async_update_data(self):
        """Load data."""
        _LOGGER.debug("Loading new sensor data for device %s", self._device_id)
        self._device = self._ally.devices[self._device_id]

        if self._type == "battery":
            self._attr_native_value = self._device["battery"]
        elif self._type == "temperature":
            self._attr_native_value = self._device["temperature"]
        elif self._type == "humidity":
            self._attr_native_value = self._device["humidity"]
