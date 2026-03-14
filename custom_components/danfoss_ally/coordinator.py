"""Coordinator support for Danfoss Ally."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass
import logging
import math
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pydanfossally import DanfossAlly, exceptions

from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)
WRITE_REFRESH_DELAY = 1.0
PENDING_WRITE_TIMEOUT = 60.0


def _format_error(err: BaseException) -> str:
    """Return a useful error string even for exceptions without a message."""
    return str(err) or err.__class__.__name__


@dataclass(slots=True)
class DanfossAllyRuntimeData:
    """Runtime data stored on a config entry."""

    client: DanfossAlly
    coordinator: DanfossAllyDataUpdateCoordinator


@dataclass(slots=True)
class PendingWrite:
    """Pending optimistic device updates awaiting confirmation from polling."""

    updates: dict[str, Any]
    expires_at: float


DanfossConfigEntry = ConfigEntry


class DanfossAllyDataUpdateCoordinator(
    DataUpdateCoordinator[dict[str, dict[str, Any]]]
):
    """Fetch and cache Danfoss Ally device data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: DanfossAlly,
        entry: DanfossConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.client = client
        self._pending_writes: dict[str, PendingWrite] = {}

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
            raise UpdateFailed(
                f"Failed to fetch Danfoss Ally devices: {_format_error(err)}"
            ) from err

        return self._apply_pending_writes(devices)

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
            raise HomeAssistantError(f"{error_message}: {_format_error(err)}") from err

        if result is False:
            raise HomeAssistantError(error_message)

        # The Danfoss cloud may briefly return stale state immediately after a write.
        await asyncio.sleep(WRITE_REFRESH_DELAY)
        await self.async_request_refresh()

    def _async_apply_optimistic_updates(
        self,
        device_id: str,
        updates: dict[str, Any],
    ) -> None:
        """Update cached data immediately after a successful local write."""
        self._register_pending_write(device_id, updates)

        if self.data is None:
            return

        new_data = {**self.data}
        new_data[device_id] = {**self.data.get(device_id, {}), **updates}
        self.async_set_updated_data(new_data)

    def _register_pending_write(self, device_id: str, updates: dict[str, Any]) -> None:
        """Record optimistic updates until the polled state reflects them."""
        existing = self._pending_writes.get(device_id)
        combined_updates = {**(existing.updates if existing else {}), **updates}
        self._pending_writes[device_id] = PendingWrite(
            updates=combined_updates,
            expires_at=time.monotonic() + PENDING_WRITE_TIMEOUT,
        )

    def _apply_pending_writes(
        self,
        devices: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """Overlay pending writes on top of freshly polled device data."""
        if not self._pending_writes:
            return devices

        now = time.monotonic()
        merged_devices = {**devices}

        for device_id, pending_write in list(self._pending_writes.items()):
            if pending_write.expires_at <= now:
                self._pending_writes.pop(device_id, None)
                continue

            if device_id not in merged_devices:
                continue

            device = merged_devices[device_id]
            unresolved_updates: dict[str, Any] = {}

            for key, expected_value in pending_write.updates.items():
                if self._values_match(device.get(key), expected_value):
                    continue

                unresolved_updates[key] = expected_value

            if not unresolved_updates:
                self._pending_writes.pop(device_id, None)
                continue

            merged_devices[device_id] = {**device, **unresolved_updates}
            self._pending_writes[device_id] = PendingWrite(
                updates=unresolved_updates,
                expires_at=pending_write.expires_at,
            )

        return merged_devices

    def _values_match(self, actual: Any, expected: Any) -> bool:
        """Compare polled and optimistic values with tolerance for floats."""
        if (
            isinstance(actual, int | float)
            and isinstance(expected, int | float)
            and not isinstance(actual, bool)
            and not isinstance(expected, bool)
        ):
            return math.isclose(float(actual), float(expected), abs_tol=0.05)

        return actual == expected
