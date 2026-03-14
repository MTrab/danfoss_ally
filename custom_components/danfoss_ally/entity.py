"""Entity helpers for Danfoss Ally."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_NAME, DOMAIN
from .coordinator import DanfossAllyDataUpdateCoordinator


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
        return self.coordinator.data[self._device_id]

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
        return bool(self.device.get("online", True))
