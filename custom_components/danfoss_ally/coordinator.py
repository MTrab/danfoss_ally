"""Coordinator support for Danfoss Ally."""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_OFF,
    STATE_ON,
    STATE_OPEN,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pydanfossally import DanfossAlly, exceptions

from .const import (
    CONF_EXTERNAL_SENSORS,
    CONF_WINDOW_SENSORS,
    DOMAIN,
    SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)
PENDING_WRITE_TIMEOUT = 60.0
TIMEOUT_RETRY_AFTER = 60.0
CONNECTION_RETRY_AFTER = 120.0
FORBIDDEN_RETRY_AFTER = 1800.0
RATE_LIMIT_RETRY_AFTER = 900.0
SERVER_ERROR_RETRY_AFTER = 600.0
GENERIC_API_RETRY_AFTER = 300.0
AUTH_FAILED_MESSAGE = (
    "Authentication failed. Check your Consumer Key and Consumer Secret."
)
WINDOW_SENSOR_DELAY = 60.0
WINDOW_RESTORE_STORE_KEY = f"{DOMAIN}_window_restore"
WINDOW_RESTORE_STORE_VERSION = 1


def _format_error(err: BaseException) -> str:
    """Return a useful error string even for exceptions without a message."""
    return str(err) or err.__class__.__name__


def _describe_api_error(err: BaseException) -> str:
    """Return a user-facing explanation for common API failures."""
    if isinstance(err, TimeoutError):
        return (
            "Danfoss Ally API timeout. Opening an issue will not help with this error."
        )
    if isinstance(err, ConnectionError):
        return "Could not reach the Danfoss Ally API."
    if isinstance(err, exceptions.ForbiddenError):
        return "Danfoss Ally API denied access (HTTP 403)."
    if isinstance(err, exceptions.RateLimitError):
        return "Danfoss Ally API rate limit reached (HTTP 429)."
    if isinstance(err, exceptions.InternalServerError):
        return "Danfoss Ally API server error (HTTP 5xx)."
    if isinstance(err, exceptions.BadRequestError):
        return "Danfoss Ally API rejected the request (HTTP 400)."
    if isinstance(err, exceptions.NotFoundError):
        return "Danfoss Ally API resource not found (HTTP 404)."
    if isinstance(err, exceptions.APIError):
        return f"Unexpected Danfoss Ally API error: {_format_error(err)}"
    return "Unexpected Danfoss Ally API error."


def _retry_after_for_error(err: BaseException) -> float:
    """Return the retry delay in seconds for common API failures."""
    if isinstance(err, TimeoutError):
        return TIMEOUT_RETRY_AFTER
    if isinstance(err, ConnectionError):
        return CONNECTION_RETRY_AFTER
    if isinstance(err, exceptions.ForbiddenError):
        return FORBIDDEN_RETRY_AFTER
    if isinstance(err, exceptions.RateLimitError):
        return RATE_LIMIT_RETRY_AFTER
    if isinstance(err, exceptions.InternalServerError):
        return SERVER_ERROR_RETRY_AFTER
    return GENERIC_API_RETRY_AFTER


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
    baseline_response_time: int | None


@dataclass(slots=True)
class ExternalTempState:
    """Track external temperature state for a device."""

    entity_id: str
    last_sent_value: float | None  # in Celsius
    last_sent_at: float  # timestamp
    unsub_state_listener: Any | None = None


@dataclass(slots=True)
class WindowSensorState:
    """Track window sensor listener and debounce state for a device."""

    entity_id: str
    pending_timer: Any | None = None
    pending_open: bool | None = None
    unsub_state_listener: Any | None = None


@dataclass(slots=True)
class WindowRestoreState:
    """Persist the thermostat state that should be restored after window close."""

    mode: str
    target_temperature: float | None


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
        self._external_temp_states: dict[str, ExternalTempState] = {}
        self._window_sensor_states: dict[str, WindowSensorState] = {}
        self._window_restore_store = Store[dict[str, dict[str, str | float | None]]](
            hass,
            WINDOW_RESTORE_STORE_VERSION,
            WINDOW_RESTORE_STORE_KEY,
        )
        self._window_restore_states: dict[str, WindowRestoreState] = {}
        self._window_restore_loaded = False
        self._refresh_in_progress = False

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch the latest device list."""
        self._refresh_in_progress = True
        try:
            try:
                if self.data is None:
                    devices = await self.client.get_devices()
                else:
                    devices = await self.client.refresh_devices()
            except exceptions.UnauthorizedError as err:
                raise ConfigEntryAuthFailed(AUTH_FAILED_MESSAGE) from err
            except (
                TimeoutError,
                ConnectionError,
                exceptions.APIError,
                exceptions.UnexpectedError,
            ) as err:
                raise UpdateFailed(
                    _describe_api_error(err),
                    retry_after=_retry_after_for_error(err),
                ) from err

            if self._is_stale_snapshot(devices):
                return self.data or devices

            return self._apply_pending_writes(devices)
        finally:
            self._refresh_in_progress = False

    async def async_request_refresh(self) -> None:
        """Request a refresh unless one is already in progress."""
        if getattr(self, "_refresh_in_progress", False):
            _LOGGER.debug(
                "Skipping refresh request because %s refresh is already in progress",
                DOMAIN,
            )
            return

        await super().async_request_refresh()

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

    async def async_set_temperature_for_mode(
        self,
        device_id: str,
        temperature: float,
        mode: str,
        *,
        optimistic_updates: dict[str, Any] | None = None,
    ) -> None:
        """Write a mode-aware temperature setpoint and refresh state."""
        await self._async_run_write(
            device_id,
            self.client.set_temperature_for_mode(device_id, temperature, mode),
            optimistic_updates=optimistic_updates,
            error_message=f"Failed to set temperature for {device_id}",
        )

    async def async_set_manual_temperature(
        self,
        device_id: str,
        temperature: float,
        *,
        optimistic_updates: dict[str, Any] | None = None,
    ) -> None:
        """Write a manual temperature override and refresh state."""
        await self._async_run_write(
            device_id,
            self.client.set_manual_temperature(device_id, temperature),
            optimistic_updates=optimistic_updates,
            error_message=f"Failed to set temperature for {device_id}",
        )

    async def async_set_external_temperature(
        self,
        device_id: str,
        temperature: float | None,
        *,
        optimistic_updates: dict[str, Any] | None = None,
    ) -> None:
        """Write an external sensor temperature and refresh state."""
        await self._async_run_write(
            device_id,
            self.client.set_external_temperature(device_id, temperature),
            optimistic_updates=optimistic_updates,
            error_message=f"Failed to set external temperature for {device_id}",
        )

    async def async_set_upper_temp(
        self,
        device_id: str,
        temperature: float,
        *,
        optimistic_updates: dict[str, Any] | None = None,
    ) -> None:
        """Write the upper temperature limit and refresh state."""
        await self._async_run_write(
            device_id,
            self.client.set_upper_temp(device_id, temperature),
            optimistic_updates=optimistic_updates,
            error_message=f"Failed to set upper temperature for {device_id}",
        )

    async def async_set_lower_temp(
        self,
        device_id: str,
        temperature: float,
        *,
        optimistic_updates: dict[str, Any] | None = None,
    ) -> None:
        """Write the lower temperature limit and refresh state."""
        await self._async_run_write(
            device_id,
            self.client.set_lower_temp(device_id, temperature),
            optimistic_updates=optimistic_updates,
            error_message=f"Failed to set lower temperature for {device_id}",
        )

    async def async_set_at_home_setting(
        self,
        device_id: str,
        temperature: float,
        *,
        optimistic_updates: dict[str, Any] | None = None,
    ) -> None:
        """Write the at-home setpoint and refresh state."""
        await self._async_run_write(
            device_id,
            self.client.set_at_home_setting(device_id, temperature),
            optimistic_updates=optimistic_updates,
            error_message=f"Failed to set at-home temperature for {device_id}",
        )

    async def async_set_leaving_home_setting(
        self,
        device_id: str,
        temperature: float,
        *,
        optimistic_updates: dict[str, Any] | None = None,
    ) -> None:
        """Write the leaving-home setpoint and refresh state."""
        await self._async_run_write(
            device_id,
            self.client.set_leaving_home_setting(device_id, temperature),
            optimistic_updates=optimistic_updates,
            error_message=f"Failed to set leaving-home temperature for {device_id}",
        )

    async def async_set_pause_setting(
        self,
        device_id: str,
        temperature: float,
        *,
        optimistic_updates: dict[str, Any] | None = None,
    ) -> None:
        """Write the pause setpoint and refresh state."""
        await self._async_run_write(
            device_id,
            self.client.set_pause_setting(device_id, temperature),
            optimistic_updates=optimistic_updates,
            error_message=f"Failed to set pause temperature for {device_id}",
        )

    async def async_set_radiator_covered(
        self,
        device_id: str,
        covered: bool,
        *,
        optimistic_updates: dict[str, Any] | None = None,
    ) -> None:
        """Write the covered-radiator mode and refresh state."""
        await self._async_run_write(
            device_id,
            self.client.set_radiator_covered(device_id, covered),
            optimistic_updates=optimistic_updates,
            error_message=f"Failed to set radiator covered for {device_id}",
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

    @property
    def external_sensors_config(self) -> dict[str, str]:
        """Return configured external sensor entity IDs by device ID."""
        if self.config_entry is None:
            return {}
        return self.config_entry.data.get(CONF_EXTERNAL_SENSORS, {})

    def get_external_sensor_entity_id(self, device_id: str) -> str | None:
        """Return configured external sensor entity ID for one device."""
        return self.external_sensors_config.get(device_id)

    @property
    def window_sensors_config(self) -> dict[str, str]:
        """Return configured window sensor entity IDs by device ID."""
        if self.config_entry is None:
            return {}
        return self.config_entry.data.get(CONF_WINDOW_SENSORS, {})

    def get_window_sensor_entity_id(self, device_id: str) -> str | None:
        """Return configured window sensor entity ID for one device."""
        return self.window_sensors_config.get(device_id)

    def get_temperature_entity_options(self) -> list[str]:
        """Return entity IDs that can provide a temperature value."""
        options: list[str] = []
        for state in self.hass.states.async_all():
            if not self._is_temperature_entity(state):
                continue
            if self._extract_temperature_celsius(state) is None:
                continue
            options.append(state.entity_id)

        options.sort()
        return options

    def get_window_entity_options(self) -> list[str]:
        """Return entity IDs that can provide an open/closed window state."""
        options: list[str] = []
        for state in self.hass.states.async_all():
            if not self._is_window_entity(state):
                continue
            options.append(state.entity_id)

        options.sort()
        return options

    async def async_set_external_sensor_entity(
        self,
        device_id: str,
        entity_id: str | None,
    ) -> None:
        """Persist the external sensor mapping and apply runtime listeners."""
        current_map = dict(self.external_sensors_config)

        if entity_id:
            current_map[device_id] = entity_id
        else:
            current_map.pop(device_id, None)

        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={
                **self.config_entry.data,
                CONF_EXTERNAL_SENSORS: current_map,
            },
        )

        if entity_id:
            await self.async_setup_external_temp_listeners()
            await self._async_handle_external_temp_change(device_id, "", entity_id)
            return

        await self.async_disable_external_temperature(device_id)

    async def async_set_window_sensor_entity(
        self,
        device_id: str,
        entity_id: str | None,
    ) -> None:
        """Persist the window sensor mapping and apply runtime listeners."""
        current_map = dict(self.window_sensors_config)

        if entity_id:
            current_map[device_id] = entity_id
        else:
            current_map.pop(device_id, None)

        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={
                **self.config_entry.data,
                CONF_WINDOW_SENSORS: current_map,
            },
        )

        if entity_id:
            await self.async_setup_window_sensor_listeners()
            await self._async_handle_window_sensor_change(device_id, entity_id)
            return

        await self.async_disable_window_sensor(device_id)

    async def async_setup_external_temp_listeners(self) -> None:
        """Set up state change listeners for all configured external temperature sensors."""
        from homeassistant.core import callback
        from homeassistant.helpers.event import async_track_state_change

        # Clear any existing listeners
        await self._async_unload_external_temp_listeners()

        external_sensors = self.external_sensors_config
        if not external_sensors:
            return

        _LOGGER.debug(
            "Setting up external temperature listeners for devices: %s",
            list(external_sensors.keys()),
        )

        for device_id, entity_id in external_sensors.items():
            if not entity_id:
                continue

            @callback
            def handle_state_change(
                entity_id: str,
                old_state: Any,
                new_state: Any,
                device_id: str = device_id,
            ) -> None:
                """Handle external temperature entity state change."""
                if new_state is None or new_state.state == "unavailable":
                    return
                self.hass.async_create_task(
                    self._async_handle_external_temp_change(
                        device_id, new_state.state, entity_id
                    )
                )

            # Register state listener
            unsub = async_track_state_change(
                self.hass,
                [entity_id],
                handle_state_change,
            )

            # Store listener for cleanup
            self._external_temp_states[device_id] = ExternalTempState(
                entity_id=entity_id,
                last_sent_value=None,
                last_sent_at=0,
                unsub_state_listener=unsub,
            )
            _LOGGER.debug(
                "External temp listener subscribed for device %s to entity %s",
                device_id,
                entity_id,
            )
            self.hass.async_create_task(
                self._async_handle_external_temp_change(device_id, "", entity_id)
            )

    async def _async_unload_external_temp_listeners(self) -> None:
        """Unsubscribe from all external temperature state listeners."""
        for state in self._external_temp_states.values():
            if state.unsub_state_listener:
                state.unsub_state_listener()
        self._external_temp_states.clear()

    async def async_disable_external_temperature(self, device_id: str) -> None:
        """Send -8000 to disable external temperature on the device and remove listener."""
        _LOGGER.debug("Disabling external temperature for device %s", device_id)

        # Remove listener for this device only
        state = self._external_temp_states.pop(device_id, None)
        if state and state.unsub_state_listener:
            state.unsub_state_listener()

        # Send -8000 to signal device to disable external temperature
        try:
            await self._async_run_write(
                device_id,
                self.client.send_command(device_id, [("ext_measured_rs", -8000)]),
                optimistic_updates=None,
                error_message=f"Failed to disable external temperature for {device_id}",
            )
            _LOGGER.debug("External temperature disabled on device %s", device_id)
        except HomeAssistantError as err:
            _LOGGER.warning("Failed to disable external temperature: %s", err)

    async def _async_handle_external_temp_change(
        self,
        device_id: str,
        new_state_str: str,
        entity_id: str,
    ) -> None:
        """Handle external temperature entity state change and send to device if needed."""
        try:
            # Get the new state value from Home Assistant
            state = self.hass.states.get(entity_id)
            if state is None or state.state == "unavailable":
                _LOGGER.debug(
                    "External temp entity %s is unavailable, not sending update",
                    entity_id,
                )
                return

            temp_celsius = self._extract_temperature_celsius(state)
            if temp_celsius is None:
                _LOGGER.warning(
                    "External temp entity %s has invalid state value: %s",
                    entity_id,
                    state.state,
                )
                return

            # Get current state tracking
            current_state = self._external_temp_states.get(device_id)
            if current_state is None:
                current_state = ExternalTempState(
                    entity_id=entity_id,
                    last_sent_value=None,
                    last_sent_at=0,
                    unsub_state_listener=None,
                )
                self._external_temp_states[device_id] = current_state

            # Check if value has actually changed
            if current_state.last_sent_value == temp_celsius:
                _LOGGER.debug(
                    "External temp for device %s unchanged (%.1f°C), skipping send",
                    device_id,
                    temp_celsius,
                )
                return

            # Send the temperature
            await self._async_send_external_temperature(device_id, temp_celsius)

            # Schedule next re-send in 30 minutes if value hasn't changed
            self._async_schedule_external_temp_resend(device_id, temp_celsius)

        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.exception("Error handling external temp change: %s", err)

    async def _async_send_external_temperature(
        self,
        device_id: str,
        temp_celsius: float,
    ) -> None:
        """Send external temperature to device via API."""
        # Convert to 0.01°C units (21.0°C → 2100)
        temp_value = int(round(temp_celsius * 100))

        _LOGGER.debug(
            "Sending external temperature %.1f°C (value: %d) to device %s",
            temp_celsius,
            temp_value,
            device_id,
        )

        try:
            await self._async_run_write(
                device_id,
                self.client.send_command(device_id, [("ext_measured_rs", temp_value)]),
                optimistic_updates=None,
                error_message=f"Failed to send external temperature to {device_id}",
            )

            # Update tracking after successful send
            current_state = self._external_temp_states.get(device_id)
            if current_state:
                current_state.last_sent_value = temp_celsius
                current_state.last_sent_at = time.monotonic()

        except HomeAssistantError as err:
            _LOGGER.warning("Failed to send external temperature: %s", err)

    def _async_schedule_external_temp_resend(
        self,
        device_id: str,
        temp_celsius: float,
    ) -> None:
        """Schedule external temperature re-send in 30 minutes."""
        from homeassistant.helpers.event import async_call_later

        async def resend_callback(now: Any) -> None:  # now is datetime, not used
            # Check if still configured
            if device_id not in self.external_sensors_config:
                return

            # Check if value has changed
            current_state = self._external_temp_states.get(device_id)
            if current_state and current_state.last_sent_value == temp_celsius:
                _LOGGER.debug(
                    "Re-sending external temperature %.1f°C to device %s (30-min timer)",
                    temp_celsius,
                    device_id,
                )
                await self._async_send_external_temperature(device_id, temp_celsius)

        # Schedule for 30 minutes from now
        async_call_later(
            self.hass,
            30 * 60,  # 1800 seconds
            resend_callback,
        )

    async def async_unload_external_temp_listeners(self) -> None:
        """Public method to unload listeners."""
        await self._async_unload_external_temp_listeners()

    async def async_setup_window_sensor_listeners(self) -> None:
        """Set up state change listeners for all configured window sensors."""
        from homeassistant.core import callback
        from homeassistant.helpers.event import async_track_state_change

        await self._async_load_window_restore_states()
        await self._async_unload_window_sensor_listeners()

        window_sensors = self.window_sensors_config
        if not window_sensors:
            return

        _LOGGER.debug(
            "Setting up window sensor listeners for devices: %s",
            list(window_sensors.keys()),
        )

        for device_id, entity_id in window_sensors.items():
            if not entity_id:
                continue

            @callback
            def handle_state_change(
                entity_id: str,
                old_state: Any,
                new_state: Any,
                device_id: str = device_id,
            ) -> None:
                """Handle window sensor entity state change."""
                del old_state
                if new_state is None:
                    return
                self.hass.async_create_task(
                    self._async_handle_window_sensor_change(device_id, entity_id)
                )

            unsub = async_track_state_change(
                self.hass,
                [entity_id],
                handle_state_change,
            )

            self._window_sensor_states[device_id] = WindowSensorState(
                entity_id=entity_id,
                pending_timer=None,
                pending_open=None,
                unsub_state_listener=unsub,
            )
            self.hass.async_create_task(
                self._async_handle_window_sensor_change(device_id, entity_id)
            )

    async def _async_unload_window_sensor_listeners(self) -> None:
        """Unsubscribe from all configured window sensor listeners."""
        for state in self._window_sensor_states.values():
            if state.pending_timer:
                state.pending_timer()
            if state.unsub_state_listener:
                state.unsub_state_listener()
        self._window_sensor_states.clear()

    async def async_unload_window_sensor_listeners(self) -> None:
        """Public method to unload window sensor listeners."""
        await self._async_unload_window_sensor_listeners()

    async def async_disable_window_sensor(self, device_id: str) -> None:
        """Remove the window sensor listener and restore state if needed."""
        runtime_state = self._window_sensor_states.pop(device_id, None)
        if runtime_state:
            if runtime_state.pending_timer:
                runtime_state.pending_timer()
            if runtime_state.unsub_state_listener:
                runtime_state.unsub_state_listener()

        if device_id in self._window_restore_states:
            await self._async_restore_window_paused_device(device_id)

    async def _async_handle_window_sensor_change(
        self,
        device_id: str,
        entity_id: str,
    ) -> None:
        """Debounce window sensor state changes before acting."""
        state = self.hass.states.get(entity_id)
        is_open = self._extract_window_open_state(state)
        if is_open is None:
            _LOGGER.debug(
                "Window sensor %s for device %s is unavailable, skipping",
                entity_id,
                device_id,
            )
            return

        runtime_state = self._window_sensor_states.get(device_id)
        if runtime_state is None:
            runtime_state = WindowSensorState(entity_id=entity_id)
            self._window_sensor_states[device_id] = runtime_state

        if runtime_state.pending_timer:
            runtime_state.pending_timer()
            runtime_state.pending_timer = None

        if is_open:
            if device_id in self._window_restore_states:
                return
        elif device_id not in self._window_restore_states:
            return

        runtime_state.pending_open = is_open
        runtime_state.pending_timer = self._async_schedule_window_action(
            device_id,
            entity_id,
            is_open,
        )

    def _async_schedule_window_action(
        self,
        device_id: str,
        entity_id: str,
        is_open: bool,
    ) -> Any:
        """Schedule the delayed pause/restore action for one window sensor."""
        from homeassistant.helpers.event import async_call_later

        async def callback(_now: Any) -> None:
            current_entity = self.window_sensors_config.get(device_id)
            runtime_state = self._window_sensor_states.get(device_id)
            if current_entity != entity_id or runtime_state is None:
                return

            runtime_state.pending_timer = None
            runtime_state.pending_open = None

            current_open = self._extract_window_open_state(
                self.hass.states.get(entity_id)
            )
            if current_open is None or current_open != is_open:
                return

            if current_open:
                await self._async_pause_device_for_open_window(device_id)
                return

            await self._async_restore_window_paused_device(device_id)

        return async_call_later(self.hass, WINDOW_SENSOR_DELAY, callback)

    async def _async_pause_device_for_open_window(self, device_id: str) -> None:
        """Pause a thermostat after the selected window sensor stayed open."""
        if device_id in self._window_restore_states:
            return

        snapshot = self._capture_window_restore_state(device_id)
        if snapshot is None:
            _LOGGER.warning(
                "Skipping window pause for %s because the current thermostat state "
                "could not be captured",
                device_id,
            )
            return

        await self.async_set_mode(
            device_id,
            "pause",
            optimistic_updates={"mode": "pause"},
        )
        self._window_restore_states[device_id] = snapshot
        await self._async_save_window_restore_states()

    async def _async_restore_window_paused_device(self, device_id: str) -> None:
        """Restore the thermostat state captured before window pause."""
        snapshot = self._window_restore_states.get(device_id)
        if snapshot is None:
            return

        current_mode = self.data.get(device_id, {}).get("mode") if self.data else None
        if current_mode != "pause":
            self._window_restore_states.pop(device_id, None)
            await self._async_save_window_restore_states()
            return

        setpoint_code = self._get_setpoint_code_for_mode(snapshot.mode)
        optimistic_updates: dict[str, Any] = {"mode": snapshot.mode}
        if snapshot.target_temperature is not None:
            optimistic_updates[setpoint_code] = snapshot.target_temperature
            if snapshot.mode == "manual":
                optimistic_updates["manual_mode_fast"] = snapshot.target_temperature

            await self.async_set_temperature_for_mode(
                device_id,
                snapshot.target_temperature,
                snapshot.mode,
                optimistic_updates=optimistic_updates,
            )
        else:
            await self.async_set_mode(
                device_id,
                snapshot.mode,
                optimistic_updates=optimistic_updates,
            )

        self._window_restore_states.pop(device_id, None)
        await self._async_save_window_restore_states()

    async def _async_load_window_restore_states(self) -> None:
        """Load persisted window restore state from Home Assistant storage."""
        if self._window_restore_loaded:
            return

        stored = await self._window_restore_store.async_load()
        self._window_restore_loaded = True
        if not stored:
            self._window_restore_states = {}
            return

        self._window_restore_states = {
            device_id: WindowRestoreState(
                mode=str(snapshot["mode"]),
                target_temperature=(
                    float(snapshot["target_temperature"])
                    if snapshot.get("target_temperature") is not None
                    else None
                ),
            )
            for device_id, snapshot in stored.items()
            if isinstance(snapshot, dict) and isinstance(snapshot.get("mode"), str)
        }

    async def _async_save_window_restore_states(self) -> None:
        """Persist the current window restore state to Home Assistant storage."""
        await self._window_restore_store.async_save(
            {
                device_id: {
                    "mode": state.mode,
                    "target_temperature": state.target_temperature,
                }
                for device_id, state in self._window_restore_states.items()
            }
        )

    def _capture_window_restore_state(
        self, device_id: str
    ) -> WindowRestoreState | None:
        """Capture the current thermostat mode and target setpoint for restore."""
        if self.data is None:
            return None

        device = self.data.get(device_id)
        if not device:
            return None

        mode = device.get("mode")
        if not isinstance(mode, str):
            return None

        return WindowRestoreState(
            mode=mode,
            target_temperature=self._get_target_temperature_for_mode(device, mode),
        )

    def _get_target_temperature_for_mode(
        self,
        device: dict[str, Any],
        mode: str,
    ) -> float | None:
        """Return the target temperature currently associated with one mode."""
        setpoint_code = self._get_setpoint_code_for_mode(mode)
        value = device.get(setpoint_code)
        if value is None and setpoint_code != "temp_set":
            value = device.get("temp_set")
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _get_setpoint_code_for_mode(self, mode: str) -> str:
        """Map a Danfoss mode to the related setpoint field."""
        if mode in {"at_home", "home"}:
            return "at_home_setting"
        if mode in {"leaving_home", "away"}:
            return "leaving_home_setting"
        if mode == "pause":
            return "pause_setting"
        if mode == "holiday":
            return "holiday_setting"
        if mode == "manual":
            return "manual_mode_fast"
        return "temp_set"

    def _is_window_entity(self, state: Any) -> bool:
        """Return whether an entity should be offered as a window source."""
        if state is None:
            return False

        if state.domain == "group":
            return state.state in {STATE_ON, STATE_OFF}

        if state.domain != "binary_sensor":
            return False

        device_class = state.attributes.get("device_class")
        return device_class in {None, "window", "opening", "door", "garage_door"}

    def _extract_window_open_state(self, state: Any) -> bool | None:
        """Normalize a window sensor state to open/closed."""
        if state is None:
            return None

        if state.state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
            return None
        if state.state in {STATE_ON, STATE_OPEN}:
            return True
        if state.state == STATE_OFF:
            return False
        return None

    def _is_temperature_entity(self, state: Any) -> bool:
        """Return whether an entity should be offered as a temperature source."""
        if state.domain != "sensor":
            return False

        entity_id = getattr(state, "entity_id", "")
        if not entity_id or "." not in entity_id:
            return False

        domain = entity_id.split(".", 1)[0]
        device_class = state.attributes.get("device_class")
        unit = state.attributes.get("unit_of_measurement")

        if device_class == "temperature":
            return True

        if unit in {"°C", "°F", "K"}:
            return True

        return (
            domain == "climate"
            and state.attributes.get("current_temperature") is not None
        )

    def _extract_temperature_celsius(self, state: Any) -> float | None:
        """Extract a temperature value from a state object."""
        if state is None:
            return None

        try:
            return float(state.state)
        except (ValueError, TypeError):
            pass

        current_temperature = state.attributes.get("current_temperature")
        if current_temperature is None:
            return None

        try:
            return float(current_temperature)
        except (ValueError, TypeError):
            return None

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
            raise ConfigEntryAuthFailed(AUTH_FAILED_MESSAGE) from err
        except (
            TimeoutError,
            ConnectionError,
            exceptions.APIError,
            exceptions.UnexpectedError,
        ) as err:
            raise HomeAssistantError(
                f"{error_message}: {_describe_api_error(err)}"
            ) from err

        if result is False:
            raise HomeAssistantError(error_message)

        # Writes rely on optimistic state until the next scheduled poll.

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
        baseline_response_time = self._get_device_response_time(device_id)
        self._pending_writes[device_id] = PendingWrite(
            updates=combined_updates,
            expires_at=time.monotonic() + PENDING_WRITE_TIMEOUT,
            baseline_response_time=baseline_response_time,
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
            if not self._has_fresh_device_response(device, pending_write):
                merged_devices[device_id] = {**device, **pending_write.updates}
                continue

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
                baseline_response_time=pending_write.baseline_response_time,
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

    def _get_device_response_time(self, device_id: str) -> int | None:
        """Return the cached response timestamp for one device."""
        if self.data is None:
            return None

        return self._coerce_response_time(
            self.data.get(device_id, {}).get("last_response_time")
        )

    def _has_fresh_device_response(
        self,
        device: dict[str, Any],
        pending_write: PendingWrite,
    ) -> bool:
        """Return whether the latest poll is newer than the write baseline."""
        if pending_write.baseline_response_time is None:
            return True

        response_time = self._coerce_response_time(device.get("last_response_time"))
        if response_time is None:
            return False

        return response_time > pending_write.baseline_response_time

    def _coerce_response_time(self, value: Any) -> int | None:
        """Normalize API timestamps so they can be compared safely."""
        if isinstance(value, bool):
            return None

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return int(value)

        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return None

        return None

    def _is_stale_snapshot(self, devices: dict[str, dict[str, Any]]) -> bool:
        """Return whether a polled snapshot should be ignored entirely."""
        if not self.data:
            return False

        incoming_response_time = self._get_snapshot_response_time(devices)
        current_response_time = self._get_snapshot_response_time(self.data)

        if incoming_response_time is None or current_response_time is None:
            return False

        return incoming_response_time <= current_response_time

    def _get_snapshot_response_time(
        self,
        devices: dict[str, dict[str, Any]],
    ) -> int | None:
        """Return the newest response timestamp found in one snapshot."""
        response_times = [
            response_time
            for device in devices.values()
            if (
                response_time := self._coerce_response_time(
                    device.get("last_response_time")
                )
            )
            is not None
        ]
        if not response_times:
            return None

        return max(response_times)
