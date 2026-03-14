"""Regression tests for pending write handling in the coordinator."""

from __future__ import annotations

import time

from custom_components.danfoss_ally.coordinator import (
    DanfossAllyDataUpdateCoordinator,
    PendingWrite,
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
