"""Regression tests for pending write handling in the coordinator."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock

import pytest
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
