"""Switch support for Danfoss Ally."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .coordinator import DanfossConfigEntry
from .entity import DanfossAllyEntity


@dataclass(frozen=True, kw_only=True)
class DanfossAllySwitchDescription(SwitchEntityDescription):
    """Describe a Danfoss Ally switch entity."""

    unique_prefix: str


SWITCHES: tuple[DanfossAllySwitchDescription, ...] = (
    DanfossAllySwitchDescription(
        key="window_toggle",
        translation_key="window_toggle",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:window-open-variant",
        entity_registry_enabled_default=False,
        unique_prefix="{} open window detection",
    ),
    DanfossAllySwitchDescription(
        key="switch",
        translation_key="pre_heat",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:heat-wave",
        entity_registry_enabled_default=False,
        unique_prefix="{} pre-heat",
    ),
    DanfossAllySwitchDescription(
        key="load_balance_enable",
        translation_key="load_balance",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:scale-balance",
        entity_registry_enabled_default=False,
        unique_prefix="{} load balance",
    ),
    DanfossAllySwitchDescription(
        key="radiator_covered",
        translation_key="radiator_covered",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:radiator-disabled",
        entity_registry_enabled_default=False,
        unique_prefix="{} radiator covered",
    ),
    DanfossAllySwitchDescription(
        key="heat_available",
        translation_key="heat_available",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:thermometer-lines",
        entity_registry_enabled_default=False,
        unique_prefix="{} heat available",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DanfossConfigEntry,
    async_add_entities,
) -> None:
    """Set up Danfoss Ally switches."""
    coordinator = entry.runtime_data.coordinator
    entities: list[DanfossAllySwitch] = []
    for device_id, device in coordinator.data.items():
        if str(device.get("model", "")).lower() == "icon zigbee module":
            continue
        for description in SWITCHES:
            if description.key in device:
                entities.append(DanfossAllySwitch(coordinator, device_id, description))

    async_add_entities(entities)


class DanfossAllySwitch(DanfossAllyEntity, SwitchEntity):
    """Representation of a Danfoss Ally switch."""

    entity_description: DanfossAllySwitchDescription

    def __init__(
        self, coordinator, device_id: str, description: DanfossAllySwitchDescription
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._attr_translation_key = description.translation_key
        self._attr_unique_id = f"{description.unique_prefix}_{device_id}_ally"

    @property
    def is_on(self) -> bool:
        """Return the current switch state."""
        return bool(self.device[self.entity_description.key])

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self.coordinator.async_send_commands(
            self._device_id,
            [(self.entity_description.key, True)],
            optimistic_updates={self.entity_description.key: True},
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self.coordinator.async_send_commands(
            self._device_id,
            [(self.entity_description.key, False)],
            optimistic_updates={self.entity_description.key: False},
        )
