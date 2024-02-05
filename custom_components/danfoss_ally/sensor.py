"""Support for Ally sensors."""
from __future__ import annotations

import logging
from enum import IntEnum

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from pydanfossally import DanfossAlly

from .const import DATA, DOMAIN, SIGNAL_ALLY_UPDATE_RECEIVED
from .entity import AllyDeviceEntity

_LOGGER = logging.getLogger(__name__)


class AllySensorType(IntEnum):
    """Supported sensor types."""

    TEMPERATURE = 0
    BATTERY = 1
    HUMIDITY = 2
    FLOOR_TEMPERATURE = 3
    VALVE_OPENING = 4
    LOAD_ESTIMATE = 5
    LOAD_ROOM_MEAN = 6
    EXTERNAL_SENSOR_TEMPERATURE = 7


SENSORS = [
    SensorEntityDescription(
        key=AllySensorType.TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=None,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        name="{} temperature",
    ),
    SensorEntityDescription(
        key=AllySensorType.BATTERY,
        device_class=SensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        name="{} battery",
    ),
    SensorEntityDescription(
        key=AllySensorType.HUMIDITY,
        device_class=SensorDeviceClass.HUMIDITY,
        entity_category=None,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        name="{} humidity",
    ),
    SensorEntityDescription(
        key=AllySensorType.FLOOR_TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=None,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        name="{} floor temperature",
    ),
    SensorEntityDescription(
        key=AllySensorType.VALVE_OPENING,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=PERCENTAGE,
        name="{} valve opening",
        icon="mdi:pipe-valve",
    ),
    SensorEntityDescription(
        key=AllySensorType.LOAD_ESTIMATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="",
        name="{} load estimate",
        icon="mdi:progress-helper",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=AllySensorType.LOAD_ROOM_MEAN,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="",
        name="{} load room mean",
        icon="mdi:progress-star",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=AllySensorType.EXTERNAL_SENSOR_TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=None,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        name="{} external sensor temperature",
        entity_registry_enabled_default=False,
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
            sensor_type = AllySensorType(sensor.key).name.lower()
            if sensor_type in ally.devices[device]:
                _LOGGER.debug(
                    "Found %s sensor for %s", sensor_type, ally.devices[device]["name"]
                )
                entities.extend(
                    [
                        AllySensor(
                            ally,
                            ally.devices[device]["name"],
                            device,
                            sensor,
                            ally.devices[device]["model"],
                        )
                    ]
                )

    if entities:
        async_add_entities(entities, True)


class AllySensor(AllyDeviceEntity, SensorEntity):
    """Representation of an Ally sensor."""

    def __init__(
        self,
        ally: DanfossAlly,
        name,
        device_id,
        description: SensorEntityDescription,
        model=None,
    ):
        """Initialize Ally binary_sensor."""
        self.entity_description = description
        self._ally = ally
        self._device = ally.devices[device_id]
        self._device_id = device_id
        self._type = AllySensorType(description.key).name.lower()
        super().__init__(name, device_id, self._type, model)

        _LOGGER.debug("Device_id: %s --- Device: %s", self._device_id, self._device)

        self._attr_native_value = None
        self._attr_extra_state_attributes = None
        self._attr_name = self.entity_description.name.format(name)
        self._attr_unique_id = "{}_{}_ally".format(
            self._type.replace("_", " "), device_id
        )

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
        _LOGGER.debug(
            "Loading new sensor data for Ally Sensor for device %s", self._device_id
        )
        self._device = self._ally.devices[self._device_id]

        if (
            self.entity_description.key == AllySensorType.TEMPERATURE
            and "local_temperature" in self._device
        ):
            self._attr_native_value = self._device["local_temperature"]
        elif (
            self.entity_description.key == AllySensorType.EXTERNAL_SENSOR_TEMPERATURE
            and "ext_measured_rs" in self._device
            and self._device["ext_measured_rs"] != -80
        ):
            self._attr_native_value = self._device["ext_measured_rs"]
        elif self._type in self._device:
            self._attr_native_value = self._device[self._type]

        # Make external sensor temperature unavailable if value is -80 (feature disabled value)
        if self.entity_description.key == AllySensorType.EXTERNAL_SENSOR_TEMPERATURE:
            self._attr_available = self._attr_native_value != float(-80)
