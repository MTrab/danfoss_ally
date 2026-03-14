"""Sensor support for Danfoss Ally."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .coordinator import DanfossConfigEntry
from .entity import DanfossAllyEntity


@dataclass(frozen=True, kw_only=True)
class DanfossAllySensorDescription(SensorEntityDescription):
    """Describe a Danfoss Ally sensor entity."""

    exists_fn: Callable[[dict[str, object]], bool]
    value_fn: Callable[[dict[str, object]], object]
    unique_prefix: str


SENSORS: tuple[DanfossAllySensorDescription, ...] = (
    DanfossAllySensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        exists_fn=lambda device: (
            "temperature" in device or "local_temperature" in device
        ),
        value_fn=lambda device: device.get(
            "local_temperature", device.get("temperature")
        ),
        unique_prefix="temperature",
    ),
    DanfossAllySensorDescription(
        key="battery",
        translation_key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda device: "battery" in device,
        value_fn=lambda device: device["battery"],
        unique_prefix="battery",
    ),
    DanfossAllySensorDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        exists_fn=lambda device: "humidity" in device,
        value_fn=lambda device: device["humidity"],
        unique_prefix="humidity",
    ),
    DanfossAllySensorDescription(
        key="floor_temperature",
        translation_key="floor_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        exists_fn=lambda device: "floor_temperature" in device,
        value_fn=lambda device: device["floor_temperature"],
        unique_prefix="floor temperature",
    ),
    DanfossAllySensorDescription(
        key="valve_opening",
        translation_key="valve_opening",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:pipe-valve",
        exists_fn=lambda device: "valve_opening" in device or "valveOpening" in device,
        value_fn=lambda device: device.get("valve_opening", device.get("valveOpening")),
        unique_prefix="valve opening",
    ),
    DanfossAllySensorDescription(
        key="load_room_mean",
        translation_key="load_room_mean",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:progress-star",
        entity_registry_enabled_default=False,
        exists_fn=lambda device: "load_room_mean" in device,
        value_fn=lambda device: device["load_room_mean"],
        unique_prefix="load room mean",
    ),
    DanfossAllySensorDescription(
        key="external_sensor_temperature",
        translation_key="external_sensor_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        exists_fn=lambda device: (
            "ext_measured_rs" in device or "external_sensor_temperature" in device
        ),
        value_fn=lambda device: device.get(
            "ext_measured_rs", device.get("external_sensor_temperature")
        ),
        unique_prefix="external sensor temperature",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DanfossConfigEntry,
    async_add_entities,
) -> None:
    """Set up Danfoss Ally sensor entities."""
    coordinator = entry.runtime_data.coordinator
    entities: list[DanfossAllySensor] = []
    for device_id, device in coordinator.data.items():
        for description in SENSORS:
            if description.exists_fn(device):
                entities.append(DanfossAllySensor(coordinator, device_id, description))

    async_add_entities(entities)


class DanfossAllySensor(DanfossAllyEntity, SensorEntity):
    """Representation of a Danfoss Ally sensor."""

    entity_description: DanfossAllySensorDescription

    def __init__(
        self, coordinator, device_id: str, description: DanfossAllySensorDescription
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._attr_translation_key = description.translation_key
        self._attr_unique_id = f"{description.unique_prefix}_{device_id}_ally"

    @property
    def native_value(self) -> object:
        """Return the current sensor value."""
        return self.entity_description.value_fn(self.device)

    @property
    def available(self) -> bool:
        """Return whether the sensor should be considered available."""
        if self.entity_description.key == "external_sensor_temperature":
            value = self.native_value
            return super().available and value not in (-80, -80.0)
        return super().available
