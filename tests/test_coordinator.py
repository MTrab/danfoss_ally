"""Regression tests for pending write handling in the coordinator."""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, State
from homeassistant.helpers.entity_registry import RegistryEntryDisabler
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed
from pydanfossally import exceptions
from custom_components.danfoss_ally.coordinator import (
    CONNECTION_RETRY_AFTER,
    DanfossAllyDataUpdateCoordinator,
    FORBIDDEN_RETRY_AFTER,
    GENERIC_API_RETRY_AFTER,
    PendingWrite,
    RATE_LIMIT_RETRY_AFTER,
    SERVER_ERROR_RETRY_AFTER,
    TIMEOUT_RETRY_AFTER,
    WindowRestoreState,
)


def test_apply_pending_writes_overlays_stale_polled_values() -> None:
    """Pending writes should mask stale server values until they are observed."""
    coordinator = object.__new__(DanfossAllyDataUpdateCoordinator)
    coordinator._pending_writes = {
        "device-1": PendingWrite(
            updates={"mode": "manual", "manual_mode_fast": 23.0},
            expires_at=time.monotonic() + 60,
            baseline_response_time=None,
        )
    }

    devices = {
        "device-1": {
            "mode": "at_home",
            "manual_mode_fast": 21.0,
            "temperature": 20.5,
        }
    }

    merged = coordinator._apply_pending_writes(devices)

    assert merged["device-1"]["mode"] == "manual"
    assert merged["device-1"]["manual_mode_fast"] == 23.0
    assert "device-1" in coordinator._pending_writes


def test_apply_pending_writes_clears_confirmed_values() -> None:
    """Pending writes should clear once polling reflects the expected values."""
    coordinator = object.__new__(DanfossAllyDataUpdateCoordinator)
    coordinator._pending_writes = {
        "device-1": PendingWrite(
            updates={"mode": "manual", "manual_mode_fast": 23.0},
            expires_at=time.monotonic() + 60,
            baseline_response_time=None,
        )
    }

    devices = {
        "device-1": {
            "mode": "manual",
            "manual_mode_fast": 23.0,
            "temperature": 20.5,
        }
    }

    merged = coordinator._apply_pending_writes(devices)

    assert merged["device-1"]["mode"] == "manual"
    assert merged["device-1"]["manual_mode_fast"] == 23.0
    assert coordinator._pending_writes == {}


def test_apply_pending_writes_waits_for_new_response_timestamp() -> None:
    """Stale poll snapshots should not override pending values."""
    coordinator = object.__new__(DanfossAllyDataUpdateCoordinator)
    coordinator._pending_writes = {
        "device-1": PendingWrite(
            updates={"mode": "manual", "manual_mode_fast": 23.0},
            expires_at=time.monotonic() + 60,
            baseline_response_time=100,
        )
    }

    devices = {
        "device-1": {
            "mode": "at_home",
            "manual_mode_fast": 21.0,
            "temperature": 20.5,
            "last_response_time": 100,
        }
    }

    merged = coordinator._apply_pending_writes(devices)

    assert merged["device-1"]["mode"] == "manual"
    assert merged["device-1"]["manual_mode_fast"] == 23.0
    assert merged["device-1"]["temperature"] == 20.5
    assert "device-1" in coordinator._pending_writes


def test_apply_pending_writes_uses_new_response_timestamp_for_confirmation() -> None:
    """A newer poll may clear pending values once it matches the write."""
    coordinator = object.__new__(DanfossAllyDataUpdateCoordinator)
    coordinator._pending_writes = {
        "device-1": PendingWrite(
            updates={"mode": "manual", "manual_mode_fast": 23.0},
            expires_at=time.monotonic() + 60,
            baseline_response_time=100,
        )
    }

    devices = {
        "device-1": {
            "mode": "manual",
            "manual_mode_fast": 23.0,
            "temperature": 20.5,
            "last_response_time": 101,
        }
    }

    merged = coordinator._apply_pending_writes(devices)

    assert merged["device-1"]["mode"] == "manual"
    assert merged["device-1"]["manual_mode_fast"] == 23.0
    assert coordinator._pending_writes == {}


def test_is_stale_snapshot_rejects_unchanged_response_timestamp() -> None:
    """Coordinator snapshots should be ignored until the API timestamp changes."""
    coordinator = object.__new__(DanfossAllyDataUpdateCoordinator)
    coordinator.data = {
        "device-1": {
            "mode": "manual",
            "last_response_time": 101,
        }
    }

    assert coordinator._is_stale_snapshot(
        {
            "device-1": {
                "mode": "at_home",
                "last_response_time": 101,
            }
        }
    )


def test_is_stale_snapshot_accepts_newer_response_timestamp() -> None:
    """Coordinator snapshots should be accepted once the API timestamp advances."""
    coordinator = object.__new__(DanfossAllyDataUpdateCoordinator)
    coordinator.data = {
        "device-1": {
            "mode": "manual",
            "last_response_time": 101,
        }
    }

    assert not coordinator._is_stale_snapshot(
        {
            "device-1": {
                "mode": "at_home",
                "last_response_time": 102,
            }
        }
    )


@pytest.mark.asyncio
async def test_update_data_uses_bulk_fetch_for_first_refresh() -> None:
    """First refresh should discover devices via the bulk endpoint."""
    coordinator = object.__new__(DanfossAllyDataUpdateCoordinator)
    coordinator.client = AsyncMock()
    coordinator.client.get_devices.return_value = {
        "device-1": {"mode": "manual", "last_response_time": 100}
    }
    coordinator.client.refresh_devices.return_value = {}
    coordinator.data = None
    coordinator._pending_writes = {}

    devices = await coordinator._async_update_data()

    assert devices["device-1"]["mode"] == "manual"
    coordinator.client.get_devices.assert_awaited_once()
    coordinator.client.refresh_devices.assert_not_called()


@pytest.mark.asyncio
async def test_update_data_uses_per_device_refresh_after_initial_load() -> None:
    """Subsequent refreshes should use per-device reads."""
    coordinator = object.__new__(DanfossAllyDataUpdateCoordinator)
    coordinator.client = AsyncMock()
    coordinator.client.get_devices.return_value = {}
    coordinator.client.refresh_devices.return_value = {
        "device-1": {"mode": "manual", "last_response_time": 101}
    }
    coordinator.data = {"device-1": {"mode": "manual", "last_response_time": 100}}
    coordinator._pending_writes = {}

    devices = await coordinator._async_update_data()

    assert devices["device-1"]["last_response_time"] == 101
    coordinator.client.refresh_devices.assert_awaited_once()
    coordinator.client.get_devices.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("side_effect", "expected_retry_after"),
    [
        (TimeoutError(), TIMEOUT_RETRY_AFTER),
        (ConnectionError(), CONNECTION_RETRY_AFTER),
        (exceptions.ForbiddenError(), FORBIDDEN_RETRY_AFTER),
        (exceptions.RateLimitError(), RATE_LIMIT_RETRY_AFTER),
        (exceptions.InternalServerError(), SERVER_ERROR_RETRY_AFTER),
        (exceptions.APIError("boom"), GENERIC_API_RETRY_AFTER),
        (exceptions.UnexpectedError(), GENERIC_API_RETRY_AFTER),
    ],
)
async def test_update_data_sets_retry_after_by_error_type(
    side_effect: BaseException,
    expected_retry_after: float,
) -> None:
    """Coordinator retries should back off differently by failure type."""
    coordinator = object.__new__(DanfossAllyDataUpdateCoordinator)
    coordinator.client = AsyncMock()
    coordinator.client.get_devices.side_effect = side_effect
    coordinator.data = None
    coordinator._pending_writes = {}

    with pytest.raises(UpdateFailed) as err_info:
        await coordinator._async_update_data()

    assert err_info.value.retry_after == expected_retry_after


@pytest.mark.asyncio
async def test_run_write_does_not_request_refresh_after_success() -> None:
    """Writes should rely on optimistic state instead of forcing a full refresh."""
    coordinator = object.__new__(DanfossAllyDataUpdateCoordinator)
    coordinator._async_apply_optimistic_updates = lambda *_args, **_kwargs: None
    coordinator.async_request_refresh = AsyncMock()

    await coordinator._async_run_write(
        "device-1",
        AsyncMock(return_value=True)(),
        optimistic_updates=None,
        error_message="boom",
    )

    coordinator.async_request_refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_async_set_pause_setting_uses_dedicated_client_helper() -> None:
    """Pause writes should call the specialized API helper."""
    coordinator = object.__new__(DanfossAllyDataUpdateCoordinator)
    pause_call = object()
    coordinator.client = Mock()
    coordinator.client.set_pause_setting = Mock(return_value=pause_call)
    coordinator.client.set_temperature_for_mode = Mock()
    coordinator._async_run_write = AsyncMock()

    await coordinator.async_set_pause_setting(
        "device-1",
        11.5,
        optimistic_updates={"pause_setting": 11.5},
    )

    coordinator.client.set_pause_setting.assert_called_once_with("device-1", 11.5)
    coordinator.client.set_temperature_for_mode.assert_not_called()
    coordinator._async_run_write.assert_awaited_once_with(
        "device-1",
        pause_call,
        optimistic_updates={"pause_setting": 11.5},
        error_message="Failed to set pause temperature for device-1",
    )


@pytest.mark.asyncio
async def test_async_request_refresh_skips_when_refresh_is_active() -> None:
    """Manual refresh requests should be ignored while another refresh is running."""
    coordinator = object.__new__(DanfossAllyDataUpdateCoordinator)
    coordinator._refresh_in_progress = True

    with patch.object(
        DataUpdateCoordinator,
        "async_request_refresh",
        new=AsyncMock(),
    ) as super_request_refresh:
        await coordinator.async_request_refresh()

    super_request_refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_async_request_refresh_calls_super_when_idle() -> None:
    """Manual refresh requests should still work when no refresh is active."""
    coordinator = object.__new__(DanfossAllyDataUpdateCoordinator)
    coordinator._refresh_in_progress = False

    with patch.object(
        DataUpdateCoordinator,
        "async_request_refresh",
        new=AsyncMock(),
    ) as super_request_refresh:
        await coordinator.async_request_refresh()

    super_request_refresh.assert_awaited_once()


class FakeStates:
    """Minimal Home Assistant states registry for coordinator tests."""

    def __init__(self, states: dict[str, State]) -> None:
        self._states = states

    def get(self, entity_id: str) -> State | None:
        return self._states.get(entity_id)

    def async_all(self) -> list[State]:
        return list(self._states.values())


class FakeBus:
    """Minimal Home Assistant event bus for coordinator tests."""

    def __init__(self) -> None:
        self.listen_once_calls: list[tuple[str, object]] = []

    def async_listen_once(self, event_type: str, callback) -> Mock:
        self.listen_once_calls.append((event_type, callback))
        return Mock()


def make_window_coordinator(
    *,
    device: dict | None = None,
    state: State | None = None,
    hass_state: CoreState = CoreState.running,
) -> DanfossAllyDataUpdateCoordinator:
    """Create a small coordinator stub for window pause tests."""
    coordinator = object.__new__(DanfossAllyDataUpdateCoordinator)
    coordinator.data = {
        "device-1": device or {"mode": "manual", "manual_mode_fast": 21.0}
    }
    coordinator._pending_writes = {}
    coordinator._external_temp_states = {}
    coordinator._window_sensor_states = {}
    coordinator._window_restore_states = {}
    coordinator._window_restore_loaded = True
    coordinator._window_restore_store = AsyncMock()
    coordinator.config_entry = SimpleNamespace(
        data={"window_sensors": {"device-1": "binary_sensor.window"}},
    )
    bus = FakeBus()
    coordinator.hass = SimpleNamespace(
        states=FakeStates(
            {"binary_sensor.window": state or State("binary_sensor.window", "on")}
        ),
        state=hass_state,
        bus=bus,
        config_entries=SimpleNamespace(async_update_entry=Mock()),
        async_create_task=lambda coro: coro,
    )
    return coordinator


@pytest.mark.asyncio
async def test_pause_device_for_open_window_stores_previous_state() -> None:
    """Open windows should switch the thermostat to pause and persist restore data."""
    coordinator = make_window_coordinator()
    coordinator.async_set_mode = AsyncMock()
    coordinator._async_save_window_restore_states = AsyncMock()

    await coordinator._async_pause_device_for_open_window("device-1")

    coordinator.async_set_mode.assert_awaited_once_with(
        "device-1",
        "pause",
        optimistic_updates={"mode": "pause"},
    )
    assert coordinator._window_restore_states == {
        "device-1": WindowRestoreState(mode="manual", target_temperature=21.0)
    }
    coordinator._async_save_window_restore_states.assert_awaited_once()


@pytest.mark.asyncio
async def test_restore_window_paused_device_restores_previous_mode_and_temperature() -> (
    None
):
    """Closing the window should restore the saved thermostat state."""
    coordinator = make_window_coordinator(
        device={"mode": "pause", "pause_setting": 7.0, "manual_mode_fast": 21.0}
    )
    coordinator._window_restore_states = {
        "device-1": WindowRestoreState(mode="manual", target_temperature=21.0)
    }
    coordinator.async_set_temperature_for_mode = AsyncMock()
    coordinator.async_set_mode = AsyncMock()
    coordinator._async_save_window_restore_states = AsyncMock()

    await coordinator._async_restore_window_paused_device("device-1")

    coordinator.async_set_temperature_for_mode.assert_awaited_once_with(
        "device-1",
        21.0,
        "manual",
        optimistic_updates={"mode": "manual", "manual_mode_fast": 21.0},
    )
    coordinator.async_set_mode.assert_not_called()
    assert coordinator._window_restore_states == {}
    coordinator._async_save_window_restore_states.assert_awaited_once()


@pytest.mark.asyncio
async def test_restore_window_paused_device_discards_stale_snapshot_if_user_resumed() -> (
    None
):
    """Manual user changes should win over an old stored restore snapshot."""
    coordinator = make_window_coordinator(
        device={"mode": "manual", "manual_mode_fast": 20.0}
    )
    coordinator._window_restore_states = {
        "device-1": WindowRestoreState(mode="at_home", target_temperature=19.0)
    }
    coordinator.async_set_temperature_for_mode = AsyncMock()
    coordinator._async_save_window_restore_states = AsyncMock()

    await coordinator._async_restore_window_paused_device("device-1")

    coordinator.async_set_temperature_for_mode.assert_not_called()
    assert coordinator._window_restore_states == {}
    coordinator._async_save_window_restore_states.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_window_sensor_change_schedules_pause_for_current_open_state() -> (
    None
):
    """Current open sensor state should schedule a pause action."""
    coordinator = make_window_coordinator(state=State("binary_sensor.window", "on"))
    cancel_callback = Mock()
    coordinator._async_schedule_window_action = Mock(return_value=cancel_callback)

    await coordinator._async_handle_window_sensor_change(
        "device-1",
        "binary_sensor.window",
    )

    coordinator._async_schedule_window_action.assert_called_once_with(
        "device-1",
        "binary_sensor.window",
        True,
    )
    assert coordinator._window_sensor_states["device-1"].pending_open is True
    assert (
        coordinator._window_sensor_states["device-1"].pending_timer is cancel_callback
    )


@pytest.mark.asyncio
async def test_handle_window_sensor_change_schedules_restore_for_current_closed_state() -> (
    None
):
    """A closed sensor at startup should schedule restore when pause state exists."""
    coordinator = make_window_coordinator(state=State("binary_sensor.window", "off"))
    coordinator._window_restore_states = {
        "device-1": WindowRestoreState(mode="manual", target_temperature=21.0)
    }
    cancel_callback = Mock()
    coordinator._async_schedule_window_action = Mock(return_value=cancel_callback)

    await coordinator._async_handle_window_sensor_change(
        "device-1",
        "binary_sensor.window",
    )

    coordinator._async_schedule_window_action.assert_called_once_with(
        "device-1",
        "binary_sensor.window",
        False,
    )
    assert coordinator._window_sensor_states["device-1"].pending_open is False


@pytest.mark.asyncio
async def test_setup_window_sensor_listeners_waits_for_hass_started_event() -> None:
    """Initial window evaluation should wait until Home Assistant startup is complete."""
    coordinator = make_window_coordinator(hass_state=CoreState.starting)
    coordinator._async_load_window_restore_states = AsyncMock()
    coordinator._async_unload_window_sensor_listeners = AsyncMock()
    coordinator._async_handle_window_sensor_change = AsyncMock()

    with patch(
        "homeassistant.helpers.event.async_track_state_change_event",
        return_value=Mock(),
    ):
        await coordinator.async_setup_window_sensor_listeners()

    coordinator._async_handle_window_sensor_change.assert_not_called()
    assert coordinator.hass.bus.listen_once_calls
    event_type, _callback = coordinator.hass.bus.listen_once_calls[0]
    assert event_type == EVENT_HOMEASSISTANT_STARTED


def test_update_window_feature_entity_registry_disables_native_entities() -> None:
    """Selecting a window source should disable the native open-window entities."""
    coordinator = make_window_coordinator()
    registry = Mock()
    registry.async_get_entity_id.side_effect = [
        "binary_sensor.device_1_open_window",
        "switch.device_1_open_window_detection",
    ]
    registry.async_get.side_effect = [
        SimpleNamespace(disabled_by=None),
        SimpleNamespace(disabled_by=None),
    ]

    with patch(
        "custom_components.danfoss_ally.coordinator.er.async_get",
        return_value=registry,
    ):
        coordinator._async_update_window_feature_entity_registry("device-1", True)

    assert registry.async_update_entity.call_args_list == [
        (
            ("binary_sensor.device_1_open_window",),
            {"disabled_by": RegistryEntryDisabler.INTEGRATION},
        ),
        (
            ("switch.device_1_open_window_detection",),
            {"disabled_by": RegistryEntryDisabler.INTEGRATION},
        ),
    ]


def test_update_window_feature_entity_registry_only_reenables_integration_disabled_entities() -> (
    None
):
    """Removing a window source should not override user-disabled entities."""
    coordinator = make_window_coordinator()
    registry = Mock()
    registry.async_get_entity_id.side_effect = [
        "binary_sensor.device_1_open_window",
        "switch.device_1_open_window_detection",
    ]
    registry.async_get.side_effect = [
        SimpleNamespace(disabled_by=RegistryEntryDisabler.INTEGRATION),
        SimpleNamespace(disabled_by=RegistryEntryDisabler.USER),
    ]

    with patch(
        "custom_components.danfoss_ally.coordinator.er.async_get",
        return_value=registry,
    ):
        coordinator._async_update_window_feature_entity_registry("device-1", False)

    registry.async_update_entity.assert_called_once_with(
        "binary_sensor.device_1_open_window",
        disabled_by=None,
    )
