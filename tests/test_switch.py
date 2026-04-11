"""Regression tests for Danfoss Ally switch entities."""

from __future__ import annotations

import pytest

from custom_components.danfoss_ally.switch import DanfossAllySwitch, SWITCHES


class FakeCoordinator:
    """Small coordinator stub for switch entity tests."""

    def __init__(self, data):
        self.data = data
        self.command_calls: list[tuple[str, list[tuple[str, object]], dict | None]] = []
        self.radiator_covered_calls: list[tuple[str, bool, dict | None]] = []
        self._window_sensor_entity_id: str | None = None

    async def async_send_commands(
        self, device_id, commands, *, optimistic_updates=None
    ):
        self.command_calls.append((device_id, commands, optimistic_updates))
        self.data[device_id] = {**self.data[device_id], **(optimistic_updates or {})}

    async def async_set_radiator_covered(
        self,
        device_id,
        covered,
        *,
        optimistic_updates=None,
    ):
        self.radiator_covered_calls.append((device_id, covered, optimistic_updates))
        self.data[device_id] = {**self.data[device_id], **(optimistic_updates or {})}

    def get_window_sensor_entity_id(self, device_id):
        return self._window_sensor_entity_id


def make_device(**overrides):
    """Create a small switch-capable thermostat payload."""
    base = {
        "id": "device-1",
        "name": "Living room",
        "model": "Danfoss Ally Thermostat",
        "online": True,
        "radiator_covered": True,
        "window_toggle": False,
        "ext_measured_rs": 25.0,
        "external_sensor_temperature": 25.0,
    }
    base.update(overrides)
    return base


def make_switch(coordinator, key: str) -> DanfossAllySwitch:
    """Create one switch entity for the selected description."""
    description = next(
        description for description in SWITCHES if description.key == key
    )
    return DanfossAllySwitch(coordinator, "device-1", description)


@pytest.mark.asyncio
async def test_turning_off_radiator_covered_clears_external_temperature() -> None:
    """Disabling covered-radiator mode should also clear ext sensor values."""
    coordinator = FakeCoordinator({"device-1": make_device()})
    entity = make_switch(coordinator, "radiator_covered")

    await entity.async_turn_off()

    assert coordinator.radiator_covered_calls == [
        (
            "device-1",
            False,
            {
                "radiator_covered": False,
                "ext_measured_rs": -80.0,
                "external_sensor_temperature": -80.0,
            },
        )
    ]


@pytest.mark.asyncio
async def test_turning_on_radiator_covered_uses_specialized_helper() -> None:
    """Enabling covered-radiator mode should use the dedicated helper."""
    coordinator = FakeCoordinator({"device-1": make_device(radiator_covered=False)})
    entity = make_switch(coordinator, "radiator_covered")

    await entity.async_turn_on()

    assert coordinator.radiator_covered_calls == [
        ("device-1", True, {"radiator_covered": True})
    ]


@pytest.mark.asyncio
async def test_other_switches_keep_generic_command_flow() -> None:
    """Non-radiator switches should continue using generic commands."""
    coordinator = FakeCoordinator({"device-1": make_device(window_toggle=False)})
    entity = make_switch(coordinator, "window_toggle")

    await entity.async_turn_on()

    assert coordinator.command_calls == [
        ("device-1", [("window_toggle", True)], {"window_toggle": True})
    ]


def test_window_toggle_becomes_unavailable_when_window_source_is_configured() -> None:
    """Native window detection switch should become unavailable when HA window source is used."""
    coordinator = FakeCoordinator({"device-1": make_device(window_toggle=False)})
    coordinator._window_sensor_entity_id = "binary_sensor.window"
    entity = make_switch(coordinator, "window_toggle")

    assert entity.available is False
