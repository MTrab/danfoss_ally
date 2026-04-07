"""Select support for Danfoss Ally."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .coordinator import DanfossConfigEntry
from .entity import DanfossAllyEntity, async_setup_dynamic_platform_entities

EXTERNAL_SENSOR_DISABLED = "disabled"

HCS_OPTIONS = {
    "quick": 1,
    "moderate": 5,
    "slow": 10,
}

HCS_SELECT = SelectEntityDescription(
    key="ctrl_alg",
    translation_key="heating_control_scaling",
    entity_category=EntityCategory.CONFIG,
    icon="mdi:car-traction-control",
    options=list(HCS_OPTIONS),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DanfossConfigEntry,
    async_add_entities,
) -> None:
    """Set up Danfoss Ally selects."""
    async_setup_dynamic_platform_entities(entry, async_add_entities, _build_entities)


def _build_entities(
    coordinator,
) -> list[DanfossAllyHcsSelect | DanfossAllyExternalTemperatureSensorSelect]:
    """Build select entities for currently discovered devices."""
    entities: list[DanfossAllyHcsSelect | DanfossAllyExternalTemperatureSensorSelect] = []
    for device_id, device in (coordinator.data or {}).items():
        if "ctrl_alg" in device:
            entities.append(DanfossAllyHcsSelect(coordinator, device_id))

        if device.get("isThermostat"):
            entities.append(
                DanfossAllyExternalTemperatureSensorSelect(coordinator, device_id)
            )

    return entities


class DanfossAllyHcsSelect(DanfossAllyEntity, SelectEntity):
    """Heating Control Scaling select."""

    entity_description = HCS_SELECT

    def __init__(self, coordinator, device_id: str) -> None:
        """Initialize the select."""
        super().__init__(coordinator, device_id)
        self._attr_translation_key = HCS_SELECT.translation_key
        self._attr_unique_id = f"{{}} heating control scaling_{device_id}_ally"

    @property
    def current_option(self) -> str | None:
        """Return the current select option."""
        if "ctrl_alg" not in self.device:
            return None

        value = int(self.device["ctrl_alg"]) & 0x0F
        option = None
        for candidate, threshold in HCS_OPTIONS.items():
            if value >= threshold:
                option = candidate
        return option

    async def async_select_option(self, option: str) -> None:
        """Set a new HCS option."""
        other_bits = int(self.device["ctrl_alg"]) & 0xF0
        value = (HCS_OPTIONS[option] & 0x0F) | other_bits
        await self.coordinator.async_send_commands(
            self._device_id,
            [("ctrl_alg", value)],
            optimistic_updates={"ctrl_alg": value},
        )


class DanfossAllyExternalTemperatureSensorSelect(DanfossAllyEntity, SelectEntity):
    """Select which HA entity should provide external room temperature."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:thermometer-lines"
    _attr_translation_key = "external_temperature_sensor_source"

    def __init__(self, coordinator, device_id: str) -> None:
        """Initialize the external temperature sensor source select."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"external_temperature_sensor_source_{device_id}_ally"

    @property
    def current_option(self) -> str | None:
        """Return currently selected source entity ID."""
        return (
            self.coordinator.get_external_sensor_entity_id(self._device_id)
            or EXTERNAL_SENSOR_DISABLED
        )

    @property
    def options(self) -> list[str]:
        """Return all selectable temperature source entities."""
        options = [
            EXTERNAL_SENSOR_DISABLED,
            *self.coordinator.get_temperature_entity_options(),
        ]

        current = self.current_option
        if current and current not in options:
            options.append(current)

        return options

    async def async_select_option(self, option: str) -> None:
        """Persist selected source and apply runtime behavior immediately."""
        entity_id = None if option == EXTERNAL_SENSOR_DISABLED else option
        await self.coordinator.async_set_external_sensor_entity(
            self._device_id,
            entity_id,
        )
        self.async_write_ha_state()
