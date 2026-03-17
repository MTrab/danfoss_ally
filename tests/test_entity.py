"""Tests for shared Danfoss Ally entity helpers."""

from __future__ import annotations

from types import SimpleNamespace

from homeassistant.helpers.entity import Entity

from custom_components.danfoss_ally.entity import (
    DanfossAllyEntity,
    async_setup_dynamic_platform_entities,
)


class FakeCoordinator:
    """Coordinator stub with listener support."""

    def __init__(self, data):
        self.data = data
        self._listeners = []

    def async_add_listener(self, listener):
        self._listeners.append(listener)

        def remove_listener():
            self._listeners.remove(listener)

        return remove_listener

    def fire_update(self) -> None:
        """Run registered update listeners."""
        for listener in list(self._listeners):
            listener()


class DummyEntity(Entity):
    """Small entity used to validate dynamic platform setup."""

    def __init__(self, unique_id: str) -> None:
        self._attr_unique_id = unique_id


class DummyDanfossEntity(DanfossAllyEntity):
    """Minimal concrete Danfoss entity for shared availability checks."""

    @property
    def name(self) -> str | None:
        return None


def test_dynamic_platform_setup_adds_new_entities_on_coordinator_updates() -> None:
    """Coordinator listeners should add entities for newly discovered devices."""
    coordinator = FakeCoordinator({"device-1": {"online": True}})
    entry = SimpleNamespace(
        runtime_data=SimpleNamespace(coordinator=coordinator),
        async_on_unload=lambda func: None,
    )
    added_batches: list[list[str]] = []

    def async_add_entities(entities):
        added_batches.append([entity.unique_id for entity in entities])

    def entity_factory(coordinator):
        return [DummyEntity(f"entity-{device_id}") for device_id in coordinator.data]

    async_setup_dynamic_platform_entities(entry, async_add_entities, entity_factory)

    assert added_batches == [["entity-device-1"]]

    coordinator.data["device-2"] = {"online": True}
    coordinator.fire_update()

    assert added_batches == [["entity-device-1"], ["entity-device-2"]]

    coordinator.fire_update()

    assert added_batches == [["entity-device-1"], ["entity-device-2"]]


def test_danfoss_entity_becomes_unavailable_when_device_disappears() -> None:
    """Entities should not crash when a previously known device disappears."""
    coordinator = FakeCoordinator(
        {
            "device-1": {
                "name": "Living room",
                "model": "Danfoss Ally Thermostat",
                "online": True,
            }
        }
    )
    entity = DummyDanfossEntity(coordinator, "device-1")

    assert entity.available is True

    coordinator.data = {}

    assert entity.available is False
    assert entity.device == {}
    assert entity.device_info["name"] == "device-1"
