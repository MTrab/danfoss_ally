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
