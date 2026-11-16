"""Sensor coverage for Danfoss Ally."""

from __future__ import annotations

from custom_components.danfoss_ally.binary_sensor import (
    BINARY_SENSORS,
    DanfossAllyBinarySensor,
)
from custom_components.danfoss_ally.sensor import DanfossAllySensor, SENSORS


class FakeCoordinator:
    """Coordinator stub used by the sensor entities."""

    def __init__(self, data):
        self.data = data
        self._window_sensor_entity_id: str | None = None

    def get_window_sensor_entity_id(self, device_id):
        return self._window_sensor_entity_id


def test_external_sensor_temperature_uses_ext_measured_rs() -> None:
    """The external sensor entity should survive on ext_measured_rs alone."""
    coordinator = FakeCoordinator(
        {
            "device-1": {
                "name": "Living room",
                "model": "Danfoss Ally Thermostat",
                "online": True,
                "ext_measured_rs": 21.75,
            }
        }
    )
    description = next(
        item for item in SENSORS if item.key == "external_sensor_temperature"
    )
    entity = DanfossAllySensor(coordinator, "device-1", description)

    assert entity.native_value == 21.75
    assert entity.available is True


def test_external_sensor_temperature_becomes_unavailable_at_disabled_value() -> None:
    """Disabled external temperature values should not surface as valid state."""
    coordinator = FakeCoordinator(
        {
            "device-1": {
                "name": "Living room",
                "model": "Danfoss Ally Thermostat",
                "online": True,
                "ext_measured_rs": -80.0,
            }
        }
    )
    description = next(
        item for item in SENSORS if item.key == "external_sensor_temperature"
    )
    entity = DanfossAllySensor(coordinator, "device-1", description)

    assert entity.available is False


def test_sensor_handles_missing_device_after_discovery() -> None:
    """Previously added sensor entities should stay safe if the device disappears."""
    coordinator = FakeCoordinator(
        {
            "device-1": {
                "name": "Living room",
                "model": "Danfoss Ally Thermostat",
                "online": True,
                "battery": 95,
            }
        }
    )
    description = next(item for item in SENSORS if item.key == "battery")
    entity = DanfossAllySensor(coordinator, "device-1", description)

    coordinator.data = {}

    assert entity.available is False
    assert entity.native_value is None


def test_open_window_binary_sensor_becomes_unavailable_when_window_source_is_configured() -> (
    None
):
    """Native open-window binary sensor should become unavailable when HA window source is used."""
    coordinator = FakeCoordinator(
        {
            "device-1": {
                "name": "Living room",
                "model": "Danfoss Ally Thermostat",
                "online": True,
                "window_open": True,
            }
        }
    )
    coordinator._window_sensor_entity_id = "binary_sensor.window"
    description = next(item for item in BINARY_SENSORS if item.key == "open_window")
    entity = DanfossAllyBinarySensor(coordinator, "device-1", description)

    assert entity.available is False


def test_open_window_binary_sensor_becomes_unavailable_when_window_detection_is_off() -> (
    None
):
    """Native open-window binary sensor should become unavailable when detection is disabled."""
    coordinator = FakeCoordinator(
        {
            "device-1": {
                "name": "Living room",
                "model": "Danfoss Ally Thermostat",
                "online": True,
                "window_open": True,
                "window_toggle": False,
            }
        }
    )
    description = next(item for item in BINARY_SENSORS if item.key == "open_window")
    entity = DanfossAllyBinarySensor(coordinator, "device-1", description)

    assert entity.available is False


def make_error_code_sensor(**device) -> DanfossAllySensor:
    """Create the error code sensor for one device payload."""
    coordinator = FakeCoordinator(
        {"device-1": {"name": "Living room", "online": True, **device}}
    )
    description = next(item for item in SENSORS if item.key == "error_code")
    return DanfossAllySensor(coordinator, "device-1", description)


def test_error_code_exposes_the_raw_fault_value() -> None:
    """The sensor reports the API value as-is, without decoding it."""
    assert make_error_code_sensor(fault=0).native_value == 0
    assert make_error_code_sensor(fault=8192).native_value == 8192


def test_error_code_falls_back_to_sw_error_code() -> None:
    """The sw_error_code status is used when fault is not reported."""
    assert make_error_code_sensor(sw_error_code=2048).native_value == 2048


def test_error_code_is_unknown_for_non_integer_values() -> None:
    """Unexpected payloads should not be reported as an error value."""
    assert make_error_code_sensor(fault="motor").native_value is None
    assert make_error_code_sensor(fault=True).native_value is None


def test_error_code_is_only_created_when_the_api_reports_it() -> None:
    """Devices without a fault status do not get the sensor."""
    description = next(item for item in SENSORS if item.key == "error_code")

    assert description.exists_fn({"fault": 0})
    assert description.exists_fn({"sw_error_code": 0})
    assert not description.exists_fn({"battery": 95})
