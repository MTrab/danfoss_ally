"""Binary sensor support for Danfoss Ally."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .coordinator import DanfossConfigEntry
from .entity import DanfossAllyEntity, async_setup_dynamic_platform_entities


@dataclass(frozen=True, kw_only=True)
class DanfossAllyBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a Danfoss Ally binary sensor."""

    exists_fn: Callable[[dict[str, object]], bool]
    value_fn: Callable[[dict[str, object]], bool]
    unique_prefix: str


BINARY_SENSORS: tuple[DanfossAllyBinarySensorDescription, ...] = (
    DanfossAllyBinarySensorDescription(
        key="open_window",
        translation_key="open_window",
        device_class=BinarySensorDeviceClass.WINDOW,
        exists_fn=lambda device: "window_open" in device,
        value_fn=lambda device: bool(device["window_open"]),
        unique_prefix="open window",
    ),
    DanfossAllyBinarySensorDescription(
        key="child_lock",
        translation_key="child_lock",
        device_class=BinarySensorDeviceClass.LOCK,
        exists_fn=lambda device: "child_lock" in device,
        value_fn=lambda device: not bool(device["child_lock"]),
        unique_prefix="child lock",
    ),
    DanfossAllyBinarySensorDescription(
        key="connectivity",
        translation_key="connectivity",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda device: "online" in device,
        value_fn=lambda device: bool(device["online"]),
        unique_prefix="connectivity",
    ),
    DanfossAllyBinarySensorDescription(
        key="setpoint_change_source",
        translation_key="setpoint_change_source",
        exists_fn=lambda device: (
            "setpointchangesource" in device or "SetpointChangeSource" in device
        ),
        value_fn=lambda device: (
            device.get("setpointchangesource", device.get("SetpointChangeSource"))
            == "Manual"
        ),
        unique_prefix="Setpoint Change Source",
    ),
    DanfossAllyBinarySensorDescription(
        key="pre_heating",
        translation_key="pre_heating",
        device_class=BinarySensorDeviceClass.HEAT,
        exists_fn=lambda device: "switch_state" in device,
        value_fn=lambda device: (
            bool(device["switch_state"]) and bool(device.get("switch", False))
        ),
        unique_prefix="Pre-Heating",
    ),
    DanfossAllyBinarySensorDescription(
        key="mounting_mode_active",
        translation_key="mounting_mode_active",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:thermostat",
        entity_registry_enabled_default=False,
        exists_fn=lambda device: "mounting_mode_active" in device,
        value_fn=lambda device: bool(device["mounting_mode_active"]),
        unique_prefix="mounting mode active",
    ),
    DanfossAllyBinarySensorDescription(
        key="heat_supply_request",
        translation_key="heat_supply_request",
        icon="mdi:gas-burner",
        entity_registry_enabled_default=False,
        exists_fn=lambda device: "heat_supply_request" in device,
        value_fn=lambda device: bool(device["heat_supply_request"]),
        unique_prefix="heat supply request",
    ),
    DanfossAllyBinarySensorDescription(
        key="thermal_actuator",
        translation_key="thermal_actuator",
        device_class=BinarySensorDeviceClass.OPENING,
        icon="mdi:pipe-valve",
        exists_fn=lambda device: "output_status" in device,
        value_fn=lambda device: bool(device["output_status"]),
        unique_prefix="Thermal actuator",
    ),
    DanfossAllyBinarySensorDescription(
        key="adaptation_run_status",
        translation_key="adaptation_run_status",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:progress-clock",
        entity_registry_enabled_default=False,
        exists_fn=lambda device: "adaptation_runstatus" in device,
        value_fn=lambda device: bool(int(device["adaptation_runstatus"]) & 0x01),
        unique_prefix="adaptation run status",
    ),
    DanfossAllyBinarySensorDescription(
        key="adaptation_run_valve_characteristic_found",
        translation_key="adaptation_run_valve_characteristic_found",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:progress-check",
        entity_registry_enabled_default=False,
        exists_fn=lambda device: "adaptation_runstatus" in device,
        value_fn=lambda device: (
            bool(int(device["adaptation_runstatus"]) & 0x02)
            and not bool(int(device["adaptation_runstatus"]) & 0x04)
        ),
        unique_prefix="adaptation run valve characteristic found",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DanfossConfigEntry,
    async_add_entities,
) -> None:
    """Set up Danfoss Ally binary sensors."""
    async_setup_dynamic_platform_entities(entry, async_add_entities, _build_entities)


def _build_entities(coordinator) -> list[DanfossAllyBinarySensor]:
    """Build binary sensor entities for currently discovered devices."""
    entities: list[DanfossAllyBinarySensor] = []
    for device_id, device in (coordinator.data or {}).items():
        for description in BINARY_SENSORS:
            if description.exists_fn(device):
                entities.append(
                    DanfossAllyBinarySensor(coordinator, device_id, description)
                )
    return entities


class DanfossAllyBinarySensor(DanfossAllyEntity, BinarySensorEntity):
    """Representation of a Danfoss Ally binary sensor."""

    entity_description: DanfossAllyBinarySensorDescription

    def __init__(
        self,
        coordinator,
        device_id: str,
        description: DanfossAllyBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._attr_translation_key = description.translation_key
        self._attr_unique_id = f"{description.unique_prefix}_{device_id}_ally"

    @property
    def available(self) -> bool:
        """Return whether the binary sensor should be available."""
        if (
            self.entity_description.key == "open_window"
            and self.uses_window_sensor_source()
        ):
            return False

        return super().available

    @property
    def is_on(self) -> bool:
        """Return the current binary sensor state."""
        try:
            return self.entity_description.value_fn(self.device)
        except (KeyError, TypeError):
            return False
