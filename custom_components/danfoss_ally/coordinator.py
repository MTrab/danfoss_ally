"""Coordinator support for Danfoss Ally."""

from __future__ import annotations

from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Any
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pydanfossally import DanfossAlly, exceptions

from .const import API_TIMEOUT, DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class DanfossAllyRuntimeData:
    """Runtime data stored on a config entry."""

    client: DanfossAlly
    coordinator: DanfossAllyDataUpdateCoordinator


DanfossConfigEntry = ConfigEntry


class DanfossAllyDataUpdateCoordinator(
    DataUpdateCoordinator[dict[str, dict[str, Any]]]
):
    """Fetch and cache Danfoss Ally device data."""

    def __init__(self, hass: HomeAssistant, client: DanfossAlly) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=None,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch the latest device list."""
        try:
            devices = await self.client.get_devices()
        except exceptions.UnauthorizedError as err:
            raise ConfigEntryAuthFailed(
                "Authentication with Danfoss Ally failed"
            ) from err
        except (
            TimeoutError,
            ConnectionError,
            exceptions.APIError,
            exceptions.UnexpectedError,
        ) as err:
            raise UpdateFailed(f"Failed to fetch Danfoss Ally devices: {err}") from err

        return devices

    async def async_set_mode(
        self,
        device_id: str,
        mode: str,
        *,
        optimistic_updates: dict[str, Any] | None = None,
    ) -> None:
        """Write a device mode and refresh state."""
        await self._async_run_write(
            device_id,
            self.client.set_mode(device_id, mode),
            optimistic_updates=optimistic_updates,
            error_message=f"Failed to set mode for {device_id}",
        )

    async def async_set_temperature(
        self,
        device_id: str,
        temperature: float,
        code: str = "manual_mode_fast",
        *,
        optimistic_updates: dict[str, Any] | None = None,
    ) -> None:
        """Write a temperature setpoint and refresh state."""
        await self._async_run_write(
            device_id,
            self.client.set_temperature(device_id, temperature, code),
            optimistic_updates=optimistic_updates,
            error_message=f"Failed to set temperature for {device_id}",
        )

    async def async_send_commands(
        self,
        device_id: str,
        commands: list[tuple[str, Any]],
        *,
        optimistic_updates: dict[str, Any] | None = None,
    ) -> None:
        """Send generic commands and refresh state."""
        await self._async_run_write(
            device_id,
            self.client.send_command(device_id, commands),
            optimistic_updates=optimistic_updates,
            error_message=f"Failed to send command for {device_id}",
        )

    async def _async_run_write(
        self,
        device_id: str,
        request: Awaitable[bool],
        *,
        optimistic_updates: dict[str, Any] | None,
        error_message: str,
    ) -> None:
        """Execute a write request, apply optimistic state and refresh."""
        if optimistic_updates:
            self._async_apply_optimistic_updates(device_id, optimistic_updates)

        try:
            result = await request
        except exceptions.UnauthorizedError as err:
            raise ConfigEntryAuthFailed(
                "Authentication with Danfoss Ally failed"
            ) from err
        except (
            TimeoutError,
            ConnectionError,
            exceptions.APIError,
            exceptions.UnexpectedError,
        ) as err:
            raise HomeAssistantError(error_message) from err

        if result is False:
            raise HomeAssistantError(error_message)

        await self.async_request_refresh()

    def _async_apply_optimistic_updates(
        self,
        device_id: str,
        updates: dict[str, Any],
    ) -> None:
        """Update cached data immediately after a successful local write."""
        if self.data is None:
            return

        new_data = {**self.data}
        new_data[device_id] = {**self.data.get(device_id, {}), **updates}
        self.async_set_updated_data(new_data)


def create_client() -> DanfossAlly:
    """Create the Danfoss Ally API client."""
    return DanfossAlly(timeout=API_TIMEOUT)
