"""Entity helpers for Danfoss Ally."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_NAME, DOMAIN
from .coordinator import DanfossAllyDataUpdateCoordinator, DanfossConfigEntry


type DanfossEntityFactory = Callable[
    [DanfossAllyDataUpdateCoordinator],
    Iterable[Entity],
]


def async_setup_dynamic_platform_entities(
    entry: DanfossConfigEntry,
    async_add_entities: Callable[[list[Entity]], None],
    entity_factory: DanfossEntityFactory,
) -> None:
    """Add entities now and whenever the coordinator discovers new devices."""
    coordinator = entry.runtime_data.coordinator
    known_unique_ids: set[str] = set()

    @callback
    def async_add_new_entities() -> None:
        new_entities: list[Entity] = []

        for entity in entity_factory(coordinator):
            if entity.unique_id is None or entity.unique_id in known_unique_ids:
                continue
            known_unique_ids.add(entity.unique_id)
            new_entities.append(entity)

        if new_entities:
            async_add_entities(new_entities)

    async_add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(async_add_new_entities))


class DanfossAllyEntity(CoordinatorEntity[DanfossAllyDataUpdateCoordinator], Entity):
    """Shared base entity for Danfoss Ally entities."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: DanfossAllyDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize the shared device entity state."""
        super().__init__(coordinator, context=device_id)
        self._device_id = device_id

    @property
    def device(self) -> dict[str, Any]:
        """Return the latest cached device data."""
        if self.coordinator.data is None:
            return {}
        return self.coordinator.data.get(self._device_id, {})

    def device_value(self, *keys: str, default: Any = None) -> Any:
        """Return the first available device value for the provided keys."""
        for key in keys:
            if key in self.device:
                return self.device[key]
        return default

    @property
    def device_info(self) -> DeviceInfo:
        """Describe the backing Danfoss device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            manufacturer=DEFAULT_NAME,
            model=self.device.get("model"),
            name=self.device.get("name", self._device_id),
        )

    @property
    def available(self) -> bool:
        """Return whether the backing device is online."""
        return self._device_id in (self.coordinator.data or {}) and bool(
            self.device.get("online", True)
        )

    def uses_window_sensor_source(self) -> bool:
        """Return whether the thermostat uses a Home Assistant window sensor source."""
        return self.coordinator.get_window_sensor_entity_id(self._device_id) is not None

    def native_window_detection_enabled(self) -> bool:
        """Return whether the native thermostat window detection is enabled."""
        return bool(self.device.get("window_toggle"))
