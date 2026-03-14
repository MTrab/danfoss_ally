"""Regression tests for Danfoss Ally climate entities."""

from __future__ import annotations

import pytest
from homeassistant.components.climate.const import PRESET_HOME

from custom_components.danfoss_ally.climate import DanfossAllyClimate


class FakeCoordinator:
    """Small coordinator stub for entity tests."""

    def __init__(self, data):
        self.data = data
        self.temperature_calls: list[tuple[str, float, str, dict | None]] = []
        self.mode_temperature_calls: list[tuple[str, float, str, dict | None]] = []
        self.manual_temperature_calls: list[tuple[str, float, dict | None]] = []
        self.mode_calls: list[tuple[str, str, dict | None]] = []
        self.command_calls: list[tuple[str, list[tuple[str, object]], dict | None]] = []

    async def async_set_mode(self, device_id, mode, *, optimistic_updates=None):
        self.mode_calls.append((device_id, mode, optimistic_updates))
        self.data[device_id] = {**self.data[device_id], **(optimistic_updates or {})}

    async def async_set_temperature(
        self,
        device_id,
        temperature,
        code="manual_mode_fast",
        *,
        optimistic_updates=None,
    ):
        self.temperature_calls.append(
            (device_id, temperature, code, optimistic_updates)
        )
        self.data[device_id] = {**self.data[device_id], **(optimistic_updates or {})}

    async def async_set_temperature_for_mode(
        self,
        device_id,
        temperature,
        mode,
        *,
        optimistic_updates=None,
    ):
        self.mode_temperature_calls.append(
            (device_id, temperature, mode, optimistic_updates)
        )
        self.data[device_id] = {**self.data[device_id], **(optimistic_updates or {})}

    async def async_set_manual_temperature(
        self,
        device_id,
        temperature,
        *,
        optimistic_updates=None,
    ):
        self.manual_temperature_calls.append(
            (device_id, temperature, optimistic_updates)
        )
        self.data[device_id] = {**self.data[device_id], **(optimistic_updates or {})}

    async def async_send_commands(
        self, device_id, commands, *, optimistic_updates=None
    ):
        self.command_calls.append((device_id, commands, optimistic_updates))
        self.data[device_id] = {**self.data[device_id], **(optimistic_updates or {})}


def make_device(**overrides):
    """Create a thermostat payload matching the v1 library shape."""
    base = {
        "id": "device-1",
        "isThermostat": True,
        "name": "Living room",
        "model": "Danfoss Ally Thermostat",
        "online": True,
        "mode": "manual",
        "manual_mode_fast": 21.0,
        "at_home_setting": 20.0,
        "leaving_home_setting": 17.0,
        "pause_setting": 7.0,
        "holiday_setting": 14.0,
        "temperature": 20.5,
        "battery": 91,
        "window_open": False,
        "work_state": "Heat",
        "output_status": True,
        "lower_temp": 5.0,
        "upper_temp": 30.0,
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_set_temperature_switches_auto_mode_to_manual_override() -> None:
    """Changing setpoint directly should switch scheduled mode to manual."""
    coordinator = FakeCoordinator({"device-1": make_device(mode="at_home")})
    entity = DanfossAllyClimate(coordinator, "device-1")

    await entity.async_set_temperature(temperature=22.0)

    assert coordinator.mode_calls == []
    assert coordinator.manual_temperature_calls == [
        (
            "device-1",
            22.0,
            {"mode": "manual", "manual_mode_fast": 22.0},
        ),
    ]


@pytest.mark.asyncio
async def test_set_temperature_repeats_manual_mode_fast_for_manual_mode() -> None:
    """Manual mode should keep writing the explicit manual setpoint."""
    coordinator = FakeCoordinator({"device-1": make_device(mode="manual")})
    entity = DanfossAllyClimate(coordinator, "device-1")

    await entity.async_set_temperature(temperature=23.0)

    assert coordinator.mode_calls == []
    assert coordinator.manual_temperature_calls == [
        (
            "device-1",
            23.0,
            {"mode": "manual", "manual_mode_fast": 23.0},
        ),
    ]


@pytest.mark.asyncio
async def test_set_preset_temperature_switches_to_requested_schedule_mode() -> None:
    """Preset-targeted writes should activate the matching Danfoss mode."""
    coordinator = FakeCoordinator({"device-1": make_device(mode="manual")})
    entity = DanfossAllyClimate(coordinator, "device-1")

    await entity.async_set_temperature(temperature=19.0, preset_mode=PRESET_HOME)

    assert coordinator.mode_temperature_calls == [
        (
            "device-1",
            19.0,
            "at_home",
            {"mode": "at_home", "at_home_setting": 19.0},
        ),
    ]


def test_current_temperature_prefers_external_sensor_when_radiator_is_covered() -> None:
    """Covered radiators should expose the external sensor temperature as current."""
    coordinator = FakeCoordinator(
        {
            "device-1": make_device(
                radiator_covered=True,
                external_sensor_temperature=19.5,
                temperature=25.0,
            )
        }
    )
    entity = DanfossAllyClimate(coordinator, "device-1")

    assert entity.current_temperature == 19.5


def test_hvac_action_uses_valve_opening_before_work_state() -> None:
    """Valve opening should override stale work_state readings."""
    coordinator = FakeCoordinator(
        {
            "device-1": make_device(
                output_status=None,
                valve_opening=0,
                work_state="Heat",
            )
        }
    )
    entity = DanfossAllyClimate(coordinator, "device-1")

    assert entity.hvac_action.value == "idle"
