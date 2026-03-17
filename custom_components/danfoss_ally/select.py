"""Select support for Danfoss Ally."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .coordinator import DanfossConfigEntry
from .entity import DanfossAllyEntity, async_setup_dynamic_platform_entities

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


def _build_entities(coordinator) -> list[DanfossAllyHcsSelect]:
    """Build select entities for currently discovered devices."""
    return [
        DanfossAllyHcsSelect(coordinator, device_id)
        for device_id, device in (coordinator.data or {}).items()
        if "ctrl_alg" in device
    ]


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
