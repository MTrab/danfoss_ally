"""Regression tests for Danfoss Ally number entities."""

from __future__ import annotations

import pytest

from custom_components.danfoss_ally.number import DanfossAllyNumber, NUMBERS


class FakeCoordinator:
    """Coordinator stub used by the number entities."""

    def __init__(self, data):
        self.data = data
        self.upper_temp_calls: list[tuple[str, float, dict | None]] = []
        self.lower_temp_calls: list[tuple[str, float, dict | None]] = []
        self.at_home_setting_calls: list[tuple[str, float, dict | None]] = []
        self.leaving_home_setting_calls: list[tuple[str, float, dict | None]] = []
        self.pause_setting_calls: list[tuple[str, float, dict | None]] = []

    async def async_set_upper_temp(
        self, device_id, temperature, *, optimistic_updates=None
    ):
        self.upper_temp_calls.append((device_id, temperature, optimistic_updates))
        self.data[device_id] = {**self.data[device_id], **(optimistic_updates or {})}

    async def async_set_lower_temp(
        self, device_id, temperature, *, optimistic_updates=None
    ):
        self.lower_temp_calls.append((device_id, temperature, optimistic_updates))
        self.data[device_id] = {**self.data[device_id], **(optimistic_updates or {})}

    async def async_set_at_home_setting(
        self, device_id, temperature, *, optimistic_updates=None
    ):
        self.at_home_setting_calls.append((device_id, temperature, optimistic_updates))
        self.data[device_id] = {**self.data[device_id], **(optimistic_updates or {})}

    async def async_set_leaving_home_setting(
        self, device_id, temperature, *, optimistic_updates=None
    ):
        self.leaving_home_setting_calls.append(
            (device_id, temperature, optimistic_updates)
        )
        self.data[device_id] = {**self.data[device_id], **(optimistic_updates or {})}

    async def async_set_pause_setting(
        self, device_id, temperature, *, optimistic_updates=None
    ):
        self.pause_setting_calls.append((device_id, temperature, optimistic_updates))
        self.data[device_id] = {**self.data[device_id], **(optimistic_updates or {})}


def make_device(**overrides):
    """Create a small number-capable thermostat payload."""
    base = {
        "id": "device-1",
        "name": "Living room",
        "model": "Danfoss Ally Thermostat",
        "online": True,
        "upper_temp": 28.0,
        "lower_temp": 7.0,
        "at_home_setting": 21.5,
        "leaving_home_setting": 17.0,
        "pause_setting": 12.0,
    }
    base.update(overrides)
    return base


def make_number(coordinator, key: str) -> DanfossAllyNumber:
    """Create one number entity for the selected description."""
    description = next(description for description in NUMBERS if description.key == key)
    return DanfossAllyNumber(coordinator, "device-1", description)


def test_number_reads_value_and_limits() -> None:
    """Temperature numbers should expose the cached value and fixed limits."""
    coordinator = FakeCoordinator({"device-1": make_device()})
    entity = make_number(coordinator, "upper_temp")

    assert entity.native_value == 28.0
    assert entity.native_min_value == 5.0
    assert entity.native_max_value == 35.0
    assert entity.native_step == 0.5


@pytest.mark.asyncio
async def test_upper_temp_uses_dedicated_helper() -> None:
    """Upper temp should route to the specialized coordinator helper."""
    coordinator = FakeCoordinator({"device-1": make_device()})
    entity = make_number(coordinator, "upper_temp")

    await entity.async_set_native_value(29.5)

    assert coordinator.upper_temp_calls == [("device-1", 29.5, {"upper_temp": 29.5})]


@pytest.mark.asyncio
async def test_lower_temp_uses_dedicated_helper() -> None:
    """Lower temp should route to the specialized coordinator helper."""
    coordinator = FakeCoordinator({"device-1": make_device()})
    entity = make_number(coordinator, "lower_temp")

    await entity.async_set_native_value(6.5)

    assert coordinator.lower_temp_calls == [("device-1", 6.5, {"lower_temp": 6.5})]


@pytest.mark.asyncio
async def test_at_home_setting_uses_dedicated_helper() -> None:
    """At-home setpoint should route to the specialized coordinator helper."""
    coordinator = FakeCoordinator({"device-1": make_device()})
    entity = make_number(coordinator, "at_home_setting")

    await entity.async_set_native_value(22.0)

    assert coordinator.at_home_setting_calls == [
        ("device-1", 22.0, {"at_home_setting": 22.0})
    ]


@pytest.mark.asyncio
async def test_leaving_home_setting_uses_dedicated_helper() -> None:
    """Leaving-home setpoint should route to the specialized coordinator helper."""
    coordinator = FakeCoordinator({"device-1": make_device()})
    entity = make_number(coordinator, "leaving_home_setting")

    await entity.async_set_native_value(16.5)

    assert coordinator.leaving_home_setting_calls == [
        ("device-1", 16.5, {"leaving_home_setting": 16.5})
    ]


@pytest.mark.asyncio
async def test_pause_setting_uses_pause_helper() -> None:
    """Pause setpoint should route to the pause fallback helper."""
    coordinator = FakeCoordinator({"device-1": make_device()})
    entity = make_number(coordinator, "pause_setting")

    await entity.async_set_native_value(11.5)

    assert coordinator.pause_setting_calls == [
        ("device-1", 11.5, {"pause_setting": 11.5})
    ]
