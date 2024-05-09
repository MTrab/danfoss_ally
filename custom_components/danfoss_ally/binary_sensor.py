"""Support for Ally binary_sensors."""
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory

from .const import DATA, DOMAIN, SIGNAL_ALLY_UPDATE_RECEIVED
from .entity import AllyDeviceEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up the Ally binary_sensor platform."""
    _LOGGER.debug("Setting up Danfoss Ally binary_sensor entities")
    ally = hass.data[DOMAIN][entry.entry_id][DATA]
    entities = []

    for device in ally.devices:
        if "window_open" in ally.devices[device]:
            _LOGGER.debug("Found window detector for %s", ally.devices[device]["name"])
            entities.extend(
                [
                    AllyBinarySensor(
                        ally,
                        ally.devices[device]["name"],
                        device,
                        "open window",
                        ally.devices[device]["model"],
                    )
                ]
            )
        if "child_lock" in ally.devices[device]:
            _LOGGER.debug(
                "Found child lock detector for %s", ally.devices[device]["name"]
            )
            entities.extend(
                [
                    AllyBinarySensor(
                        ally,
                        ally.devices[device]["name"],
                        device,
                        "child lock",
                        ally.devices[device]["model"],
                    )
                ]
            )
        if (
            "online" in ally.devices[device]
        ):  # not ally.devices[device]["isThermostat"]:
            _LOGGER.debug(
                "Found connection sensor for %s", ally.devices[device]["name"]
            )
            entities.extend(
                [
                    AllyBinarySensor(
                        ally,
                        ally.devices[device]["name"],
                        device,
                        "connectivity",
                        ally.devices[device]["model"],
                    )
                ]
            )
        if "SetpointChangeSource" in ally.devices[device]:
            _LOGGER.debug(
                "Found SetpointChangeSource detector for %s",
                ally.devices[device]["name"],
            )
            entities.extend(
                [
                    AllyBinarySensor(
                        ally,
                        ally.devices[device]["name"],
                        device,
                        "Setpoint Change Source",
                        ally.devices[device]["model"],
                    )
                ]
            )
        if "switch_state" in ally.devices[device]:
            _LOGGER.debug(
                "Found Pre-Heating detector for %s", ally.devices[device]["name"]
            )
            entities.extend(
                [
                    AllyBinarySensor(
                        ally,
                        ally.devices[device]["name"],
                        device,
                        "Pre-Heating",
                        ally.devices[device]["model"],
                    )
                ]
            )
        if "mounting_mode_active" in ally.devices[device]:
            _LOGGER.debug(
                "Found mounting mode active detector for %s",
                ally.devices[device]["name"],
            )
            entities.extend(
                [
                    AllyBinarySensor(
                        ally,
                        ally.devices[device]["name"],
                        device,
                        "mounting mode active",
                        ally.devices[device]["model"],
                    )
                ]
            )
        if "heat_supply_request" in ally.devices[device]:
            _LOGGER.debug(
                "Found heat_supply_request detector for %s",
                ally.devices[device]["name"],
            )
            entities.extend(
                [
                    AllyBinarySensor(
                        ally,
                        ally.devices[device]["name"],
                        device,
                        "heat supply request",
                        ally.devices[device]["model"],
                    )
                ]
            )
        if "boiler_relay" in ally.devices[device]:
            _LOGGER.debug(
                "Found boiler relay_detector for %s", ally.devices[device]["name"]
            )
            entities.extend(
                [
                    AllyBinarySensor(
                        ally,
                        ally.devices[device]["name"],
                        device,
                        "boiler relay",
                        ally.devices[device]["model"],
                    )
                ]
            )
        if "output_status" in ally.devices[device]:
            _LOGGER.debug(
                "Found output_status_detector for %s", ally.devices[device]["name"]
            )
            entities.extend(
                [
                    AllyBinarySensor(
                        ally,
                        ally.devices[device]["name"],
                        device,
                        "Thermal actuator",
                        ally.devices[device]["model"],
                    )
                ]
            )
        if "adaptation_runstatus" in ally.devices[device]:
            _LOGGER.debug(
                "Found adaptation_runstatus for %s", ally.devices[device]["name"]
            )
            entities.extend(
                [
                    AllyBinarySensor(
                        ally,
                        ally.devices[device]["name"],
                        device,
                        "adaptation run status",
                        ally.devices[device]["model"],
                    )
                ]
            )
            entities.extend(
                [
                    AllyBinarySensor(
                        ally,
                        ally.devices[device]["name"],
                        device,
                        "adaptation run valve characteristic found",
                        ally.devices[device]["model"],
                    )
                ]
            )

    if entities:
        async_add_entities(entities, True)


class AllyBinarySensor(AllyDeviceEntity, BinarySensorEntity):
    """Representation of an Ally binary_sensor."""

    def __init__(self, ally, name, device_id, device_type, model):
        """Initialize Ally binary_sensor."""
        self._ally = ally
        self._device = ally.devices[device_id]
        self._device_id = device_id
        self._type = device_type
        super().__init__(name, device_id, device_type, model)

        _LOGGER.debug("Device_id: %s --- Device: %s", self._device_id, self._device)

        self._type = device_type

        self._unique_id = f"{device_type}_{device_id}_ally"

        self._state = None

        if self._type == "link":
            self._state = self._device["online"]
        elif self._type == "open window":
            self._state = bool(self._device["window_open"])
        elif self._type == "child lock":
            self._state = not bool(self._device["child_lock"])
        elif self._type == "connectivity":
            self._state = bool(self._device["online"])
            self.entity_description = BinarySensorEntityDescription(
                key=0, entity_category=EntityCategory.DIAGNOSTIC
            )
        elif self._type == "Setpoint Change Source":
            self._state = bool(self._device["SetpointChangeSource"] == "Manual")
        elif self._type == "Pre-Heating":
            self._state = (
                bool(self._device["switch_state"])
                and "switch" in self._device
                and bool(self._device["switch"])
            )
        elif self._type == "mounting mode active":
            self._state = self._device["mounting_mode_active"]
            self.entity_description = BinarySensorEntityDescription(
                key=2,
                entity_category=EntityCategory.DIAGNOSTIC,
                icon="mdi:thermostat",
                entity_registry_enabled_default=False,
            )
        elif self._type == "heat supply request":
            self._state = self._device["heat_supply_request"]
            self.entity_description = BinarySensorEntityDescription(
                key=4, icon="mdi:gas-burner", entity_registry_enabled_default=False
            )
        elif self._type == "Thermal actuator":
            self._state = self._device["output_status"]
            self.entity_description = BinarySensorEntityDescription(
                key=4, icon="mdi:pipe-valve"
            )
        elif self._type == "adaptation run status":
            self._state = bool(int(self._device["adaptation_runstatus"]) & 0x01)
            self.entity_description = BinarySensorEntityDescription(
                key=5,
                entity_category=EntityCategory.DIAGNOSTIC,
                icon="mdi:progress-clock",
                entity_registry_enabled_default=False,
            )
        elif self._type == "adaptation run valve characteristic found":
            self._state = bool(
                int(self._device["adaptation_runstatus"]) & 0x02
            ) and not bool(int(self._device["adaptation_runstatus"]) & 0x04)
            self.entity_description = BinarySensorEntityDescription(
                key=6,
                entity_category=EntityCategory.DIAGNOSTIC,
                icon="mdi:progress-check",
                entity_registry_enabled_default=False,
            )

    async def async_added_to_hass(self):
        """Register for sensor updates."""

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_ALLY_UPDATE_RECEIVED,
                self._async_update_callback,
            )
        )

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} {self._type}"

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._state

    @property
    def device_class(self):
        """Return the class of this sensor."""
        if self._type == "link":
            return BinarySensorDeviceClass.CONNECTIVITY
        elif self._type == "open window":
            return BinarySensorDeviceClass.WINDOW
        elif self._type == "child lock":
            return BinarySensorDeviceClass.LOCK
        elif self._type == "connectivity":
            return BinarySensorDeviceClass.CONNECTIVITY
        elif self._type == "banner control":
            return BinarySensorDeviceClass.TAMPER
        elif self._type == "Pre-Heating":
            return BinarySensorDeviceClass.HEAT
        elif self._type == "adaptation run status":
            return BinarySensorDeviceClass.RUNNING
        elif self._type == "Thermal actuator":
            return BinarySensorDeviceClass.OPENING
        return None

    @callback
    def _async_update_callback(self):
        """Update and write state."""
        self._async_update_data()
        self.schedule_update_ha_state()

    @callback
    def _async_update_data(self):
        """Load data."""
        _LOGGER.debug("Loading new binary_sensor data for device %s", self._device_id)
        self._device = self._ally.devices[self._device_id]

        if self._type == "link":
            self._state = self._device["online"]
        elif self._type == "open window":
            self._state = bool(self._device["window_open"])
        elif self._type == "child lock":
            self._state = not bool(self._device["child_lock"])
        elif self._type == "connectivity":
            self._state = bool(self._device["online"])
        elif self._type == "Setpoint Change Source":
            self._state = bool(self._device["SetpointChangeSource"] == "Manual")
        elif self._type == "Pre-Heating":
            self._state = (
                bool(self._device["switch_state"])
                and "switch" in self._device
                and bool(self._device["switch"])
            )
        elif self._type == "mounting mode active":
            self._state = self._device["mounting_mode_active"]
        elif self._type == "heat supply request":
            self._state = self._device["heat_supply_request"]
        elif self._type == "boiler relay":
            self._state = self._device["boiler_relay"]
        elif self._type == "Thermal actuator":
            self._state = self._device["output_status"]
        elif self._type == "adaptation run status":
            self._state = bool(int(self._device["adaptation_runstatus"]) & 0x01)
        elif self._type == "adaptation run valve characteristic found":
            self._state = bool(
                int(self._device["adaptation_runstatus"]) & 0x02
            ) and not bool(int(self._device["adaptation_runstatus"]) & 0x04)
