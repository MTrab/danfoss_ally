"""Regression tests for Danfoss Ally climate entities."""

from __future__ import annotations

import pytest
from homeassistant.components.climate.const import PRESET_HOME

from custom_components.danfoss_ally.climate import DanfossAllyClimate
from custom_components.danfoss_ally.const import PRESET_HOLIDAY, PRESET_PAUSE


class FakeCoordinator:
    """Small coordinator stub for entity tests."""

    def __init__(self, data):
        self.data = data
        self.temperature_calls: list[tuple[str, float, str, dict | None]] = []
        self.mode_temperature_calls: list[tuple[str, float, str, dict | None]] = []
        self.manual_temperature_calls: list[tuple[str, float, dict | None]] = []
        self.external_temperature_calls: list[
            tuple[str, float | None, dict | None]
        ] = []
        self.window_state_calls: list[tuple[str, bool, dict | None]] = []
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

    async def async_set_external_temperature(
        self,
        device_id,
        temperature,
        *,
        optimistic_updates=None,
    ):
        self.external_temperature_calls.append(
            (device_id, temperature, optimistic_updates)
        )
        self.data[device_id] = {**self.data[device_id], **(optimistic_updates or {})}

    async def async_set_window_state_open(
        self,
        device_id,
        window_open,
        *,
        optimistic_updates=None,
    ):
        self.window_state_calls.append((device_id, window_open, optimistic_updates))
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


def test_preset_modes_only_expose_supported_api_presets() -> None:
    """Only real API-backed presets should be exposed."""
    coordinator = FakeCoordinator({"device-1": make_device(mode="manual")})
    entity = DanfossAllyClimate(coordinator, "device-1")

    assert entity.preset_modes == [PRESET_HOME, "away", PRESET_PAUSE, PRESET_HOLIDAY]


def test_manual_mode_has_no_preset() -> None:
    """Manual is a mode, not a preset."""
    coordinator = FakeCoordinator({"device-1": make_device(mode="manual")})
    entity = DanfossAllyClimate(coordinator, "device-1")

    assert entity.preset_mode is None


def test_holiday_mode_maps_to_holiday_preset() -> None:
    """Holiday should be exposed as a single preset."""
    coordinator = FakeCoordinator({"device-1": make_device(mode="holiday")})
    entity = DanfossAllyClimate(coordinator, "device-1")

    assert entity.preset_mode == PRESET_HOLIDAY


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


def test_current_temperature_prefers_external_sensor_when_available() -> None:
    """External sensor readings should override local temperature when present."""
    coordinator = FakeCoordinator(
        {
            "device-1": make_device(
                radiator_covered=False,
                external_sensor_temperature=18.5,
                temperature=25.0,
            )
        }
    )
    entity = DanfossAllyClimate(coordinator, "device-1")

    assert entity.current_temperature == 18.5


def test_current_temperature_prefers_ext_measured_rs_when_available() -> None:
    """The raw external sensor value should also override local temperature."""
    coordinator = FakeCoordinator(
        {
            "device-1": make_device(
                radiator_covered=False,
                ext_measured_rs=25.0,
                temperature=20.7,
            )
        }
    )
    entity = DanfossAllyClimate(coordinator, "device-1")

    assert entity.current_temperature == 25.0


@pytest.mark.asyncio
async def test_set_external_temperature_enables_radiator_covered() -> None:
    """Writing an external temperature should enable covered-radiator mode."""
    coordinator = FakeCoordinator({"device-1": make_device(radiator_covered=False)})
    entity = DanfossAllyClimate(coordinator, "device-1")

    await entity.async_set_external_temperature(temperature=25.0)

    assert coordinator.external_temperature_calls == [
        (
            "device-1",
            25.0,
            {
                "radiator_covered": True,
                "ext_measured_rs": 25.0,
                "external_sensor_temperature": 25.0,
            },
        )
    ]


@pytest.mark.asyncio
async def test_set_window_state_open_uses_shared_helper() -> None:
    """The climate service should reuse the shared window-state helper."""
    coordinator = FakeCoordinator({"device-1": make_device(window_open=False)})
    entity = DanfossAllyClimate(coordinator, "device-1")

    await entity.async_set_window_state_open(window_open=True)

    assert coordinator.window_state_calls == [("device-1", True, {"window_open": True})]


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


def test_hvac_action_prefers_no_heat_work_state_over_output_status() -> None:
    """A NoHeat work_state should not be forced into heating by output_status."""
    coordinator = FakeCoordinator(
        {
            "device-1": make_device(
                output_status=True,
                work_state="NoHeat",
            )
        }
    )
    entity = DanfossAllyClimate(coordinator, "device-1")

    assert entity.hvac_action.value == "idle"


def test_hvac_action_uses_heat_work_state_when_valve_opening_missing() -> None:
    """A Heat work_state should still report heating without valve telemetry."""
    coordinator = FakeCoordinator(
        {
            "device-1": make_device(
                output_status=True,
                work_state="Heat",
                valve_opening=None,
            )
        }
    )
    entity = DanfossAllyClimate(coordinator, "device-1")

    assert entity.hvac_action.value == "heating"


def test_hvac_action_uses_valve_opening_for_heat_work_state() -> None:
    """Valve opening should confirm active heating when Heat is reported."""
    coordinator = FakeCoordinator(
        {
            "device-1": make_device(
                output_status=None,
                valve_opening=18,
                work_state="Heat",
            )
        }
    )
    entity = DanfossAllyClimate(coordinator, "device-1")

    assert entity.hvac_action.value == "heating"


def test_hvac_action_falls_back_to_output_status_without_work_state() -> None:
    """Devices without work_state should still use output_status as a fallback."""
    coordinator = FakeCoordinator(
        {
            "device-1": make_device(
                output_status=False,
                work_state=None,
                valve_opening=None,
            )
        }
    )
    entity = DanfossAllyClimate(coordinator, "device-1")

    assert entity.hvac_action.value == "idle"
