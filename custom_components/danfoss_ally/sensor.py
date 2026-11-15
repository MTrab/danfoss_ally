"""Sensor support for Danfoss Ally."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

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
from .entity import DanfossAllyEntity, async_setup_dynamic_platform_entities


NO_ERROR_STATE = "none"

# Radiator thermostat "SW error code" bit field (Zigbee attribute 0x4000 of the
# diagnostics cluster 0x0B05), as listed in the Danfoss Ally radiator
# thermostat Zigbee specification. Bit n is shown on the device as E(n+1).
ERROR_CODE_DESCRIPTIONS: dict[int, str] = {
    1: "Top PCB sensor error",
    2: "Side PCB sensor error",
    3: "Non-volatile memory error",
    4: "Unknown hardware error",
    6: "Motor error",
    8: "Invalid internal communication",
    10: "Invalid clock information",
    12: "Radio communication error",
    13: "Encoder jammed",
    14: "Low battery",
    15: "Critical low battery",
}
UNKNOWN_ERROR_DESCRIPTION = "Unknown error"


def _raw_error_code(device: dict[str, object]) -> int | None:
    """Return the raw error bit field reported for a thermostat."""
    value = device.get("fault", device.get("sw_error_code"))
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _active_error_numbers(raw: int) -> list[int]:
    """Return the E-numbers of every bit set in the error bit field."""
    return [bit + 1 for bit in range(raw.bit_length()) if raw & (1 << bit)]


def _has_error_code(device: dict[str, object]) -> bool:
    """Return whether the device is a radiator thermostat reporting error codes."""
    return (
        bool(device.get("isThermostat"))
        and "Icon" not in str(device.get("model", ""))
        and ("fault" in device or "sw_error_code" in device)
    )


def _error_code_state(device: dict[str, object]) -> str | None:
    """Return the active error codes, for example "E6, E14"."""
    raw = _raw_error_code(device)
    if raw is None:
        return None
    if raw == 0:
        return NO_ERROR_STATE
    return ", ".join(f"E{number}" for number in _active_error_numbers(raw))


def _error_code_attributes(device: dict[str, object]) -> dict[str, Any] | None:
    """Return the raw bit field and a description of every active error."""
    raw = _raw_error_code(device)
    if raw is None:
        return None
    return {
        "raw_value": raw,
        "errors": [
            f"E{number}: "
            f"{ERROR_CODE_DESCRIPTIONS.get(number, UNKNOWN_ERROR_DESCRIPTION)}"
            for number in _active_error_numbers(raw)
        ],
    }


@dataclass(frozen=True, kw_only=True)
class DanfossAllySensorDescription(SensorEntityDescription):
    """Describe a Danfoss Ally sensor entity."""

    exists_fn: Callable[[dict[str, object]], bool]
    value_fn: Callable[[dict[str, object]], object]
    attributes_fn: Callable[[dict[str, object]], dict[str, Any] | None] | None = None
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
    DanfossAllySensorDescription(
        key="error_code",
        translation_key="error_code",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert-circle-outline",
        exists_fn=_has_error_code,
        value_fn=_error_code_state,
        attributes_fn=_error_code_attributes,
        unique_prefix="error code",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DanfossConfigEntry,
    async_add_entities,
) -> None:
    """Set up Danfoss Ally sensor entities."""
    async_setup_dynamic_platform_entities(entry, async_add_entities, _build_entities)


def _build_entities(coordinator) -> list[DanfossAllySensor]:
    """Build sensor entities for currently discovered devices."""
    entities: list[DanfossAllySensor] = []
    for device_id, device in (coordinator.data or {}).items():
        for description in SENSORS:
            if description.exists_fn(device):
                entities.append(DanfossAllySensor(coordinator, device_id, description))
    return entities


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
        try:
            return self.entity_description.value_fn(self.device)
        except (KeyError, TypeError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra details for sensors that provide them."""
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(self.device)

    @property
    def available(self) -> bool:
        """Return whether the sensor should be considered available."""
        if self.entity_description.key == "external_sensor_temperature":
            value = self.native_value
            return super().available and value not in (-80, -80.0)
        return super().available
