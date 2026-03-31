"""Number support for Danfoss Ally."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.components.number import NumberEntityDescription
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .coordinator import DanfossConfigEntry
from .entity import DanfossAllyEntity, async_setup_dynamic_platform_entities

MIN_TEMPERATURE = 5.0
MAX_TEMPERATURE = 35.0
TEMPERATURE_STEP = 0.5


@dataclass(frozen=True, kw_only=True)
class DanfossAllyNumberDescription(NumberEntityDescription):
    """Describe a Danfoss Ally number entity."""

    unique_prefix: str


NUMBERS: tuple[DanfossAllyNumberDescription, ...] = (
    DanfossAllyNumberDescription(
        key="upper_temp",
        translation_key="upper_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_min_value=MIN_TEMPERATURE,
        native_max_value=MAX_TEMPERATURE,
        native_step=TEMPERATURE_STEP,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        unique_prefix="upper temperature",
    ),
    DanfossAllyNumberDescription(
        key="lower_temp",
        translation_key="lower_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_min_value=MIN_TEMPERATURE,
        native_max_value=MAX_TEMPERATURE,
        native_step=TEMPERATURE_STEP,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        unique_prefix="lower temperature",
    ),
    DanfossAllyNumberDescription(
        key="at_home_setting",
        translation_key="at_home_setting",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_min_value=MIN_TEMPERATURE,
        native_max_value=MAX_TEMPERATURE,
        native_step=TEMPERATURE_STEP,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        unique_prefix="at home setting",
    ),
    DanfossAllyNumberDescription(
        key="leaving_home_setting",
        translation_key="leaving_home_setting",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_min_value=MIN_TEMPERATURE,
        native_max_value=MAX_TEMPERATURE,
        native_step=TEMPERATURE_STEP,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        unique_prefix="leaving home setting",
    ),
    DanfossAllyNumberDescription(
        key="pause_setting",
        translation_key="pause_setting",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_min_value=MIN_TEMPERATURE,
        native_max_value=MAX_TEMPERATURE,
        native_step=TEMPERATURE_STEP,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        unique_prefix="pause setting",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DanfossConfigEntry,
    async_add_entities,
) -> None:
    """Set up Danfoss Ally numbers."""
    async_setup_dynamic_platform_entities(entry, async_add_entities, _build_entities)


def _build_entities(coordinator) -> list[DanfossAllyNumber]:
    """Build number entities for currently discovered devices."""
    entities: list[DanfossAllyNumber] = []
    for device_id, device in (coordinator.data or {}).items():
        for description in NUMBERS:
            if description.key in device:
                entities.append(DanfossAllyNumber(coordinator, device_id, description))
    return entities


class DanfossAllyNumber(DanfossAllyEntity, NumberEntity):
    """Representation of a Danfoss Ally number."""

    entity_description: DanfossAllyNumberDescription

    def __init__(
        self, coordinator, device_id: str, description: DanfossAllyNumberDescription
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._attr_translation_key = description.translation_key
        self._attr_unique_id = f"{description.unique_prefix}_{device_id}_ally"

    @property
    def native_value(self) -> float | None:
        """Return the current number value."""
        value = self.device.get(self.entity_description.key)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set the number value."""
        temperature = float(value)
        optimistic_updates = {self.entity_description.key: temperature}

        if self.entity_description.key == "upper_temp":
            await self.coordinator.async_set_upper_temp(
                self._device_id,
                temperature,
                optimistic_updates=optimistic_updates,
            )
            return

        if self.entity_description.key == "lower_temp":
            await self.coordinator.async_set_lower_temp(
                self._device_id,
                temperature,
                optimistic_updates=optimistic_updates,
            )
            return

        if self.entity_description.key == "at_home_setting":
            await self.coordinator.async_set_at_home_setting(
                self._device_id,
                temperature,
                optimistic_updates=optimistic_updates,
            )
            return

        if self.entity_description.key == "leaving_home_setting":
            await self.coordinator.async_set_leaving_home_setting(
                self._device_id,
                temperature,
                optimistic_updates=optimistic_updates,
            )
            return

        await self.coordinator.async_set_pause_setting(
            self._device_id,
            temperature,
            optimistic_updates=optimistic_updates,
        )
