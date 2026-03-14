"""Sensor coverage for Danfoss Ally."""

from __future__ import annotations

from custom_components.danfoss_ally.sensor import DanfossAllySensor, SENSORS


class FakeCoordinator:
    """Coordinator stub used by the sensor entities."""

    def __init__(self, data):
        self.data = data


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
