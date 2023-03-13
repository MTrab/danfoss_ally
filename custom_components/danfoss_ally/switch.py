"""Support for Ally switched."""
from __future__ import annotations

import logging
from datetime import datetime
from enum import IntEnum

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory

from .const import DATA, DOMAIN, SIGNAL_ALLY_UPDATE_RECEIVED
from .entity import AllyDeviceEntity

_LOGGER = logging.getLogger(__name__)


class AllySwitchType(IntEnum):
    """Supported sensor types."""


#    DETECT_WINDOW_OPEN = 0

SWITCHES = [
    SwitchEntityDescription(
        key="window_toggle",
        entity_category=EntityCategory.CONFIG,
        name="{} Open window detection",
        device_class="switch",
        icon="mdi:window-open-variant",
        entity_registry_enabled_default=False,
    ),
    SwitchEntityDescription(
        key="switch",
        entity_category=EntityCategory.CONFIG,
        name="{} Pre-Heat",
        device_class="switch",
        icon="mdi:heat-wave",
        entity_registry_enabled_default=False,
    ),
    SwitchEntityDescription(
        key="load_balance_enable",
        entity_category=EntityCategory.CONFIG,
        name="{} Load balance",
        device_class="switch",
        icon="mdi:scale-balance",
        entity_registry_enabled_default=False,
    ),
    SwitchEntityDescription(
        key="radiator_covered",
        entity_category=EntityCategory.CONFIG,
        name="{} Radiator covered",
        device_class="switch",
        icon="mdi:radiator-disabled",
        entity_registry_enabled_default=False,
    ),
    SwitchEntityDescription(
        key="heat_available",
        entity_category=EntityCategory.CONFIG,
        name="{} Heat available",
        device_class="switch",
        icon="mdi:thermometer-lines",
        entity_registry_enabled_default=False,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up the Ally switch platform."""
    _LOGGER.debug("Setting up Danfoss Ally switch entities")
    ally = hass.data[DOMAIN][entry.entry_id][DATA]
    entities = []

    for device in ally.devices:
        # if "window_toggle" in ally.devices[device]:
        #     _LOGGER.debug("Found switch for window open detection: %s", ally.devices[device]["name"])
        #     entities.extend(
        #         [
        #             AllyOpenWindowDetectionSwitch(
        #                 ally,
        #                 ally.devices[device]["name"],
        #                 device,
        #                 SWITCHES[AllySwitchType.DETECT_WINDOW_OPEN],
        #                 ally.devices[device]["model"],
        #             )
        #         ]
        #     )
        if (
            "model" in ally.devices[device]
            and ally.devices[device]["model"].lower() != "icon zigbee module"
        ):  # Do not show Pre-Hear for zigbee module
            for switch in SWITCHES:
                if (
                    switch.key
                    in [
                        "window_toggle",
                        "switch",
                        "load_balance_enable",
                        "radiator_covered",
                        "heat_available",
                    ]
                    and switch.key in ally.devices[device]
                ):
                    _LOGGER.debug(
                        "Found switch for setting: %s", ally.devices[device]["name"]
                    )
                    entities.extend(
                        [
                            AllyGenericSwitch(
                                ally,
                                ally.devices[device]["name"],
                                device,
                                switch,
                                ally.devices[device]["model"],
                            )
                        ]
                    )

    if entities:
        async_add_entities(entities, True)


class AllyBaseSwitch(AllyDeviceEntity, SwitchEntity):
    """Base class of a switch"""

    def __init__(
        self,
        ally,
        name,
        device_id,
        description: SwitchEntityDescription,
        model,
        skipdelayafterwrite=2,
    ):
        """Initialize Ally switch."""
        self.entity_description = description
        self._ally = ally
        self._device = ally.devices[device_id]
        self._device_id = device_id
        self._name = name
        self._type = description.name.lower()
        self._latest_write_time = None
        self._skipdelayafterwrite = skipdelayafterwrite

        super().__init__(name, device_id, self._type, model)

        _LOGGER.debug("Device_id: %s --- Device: %s", self._device_id, self._device)

        self._attr_is_on = None
        self._attr_extra_state_attributes = None
        self._attr_name = self.entity_description.name.format(name)
        self._attr_unique_id = "{}_{}_ally".format(self._type, device_id)

    async def async_added_to_hass(self):
        """Register for sensor updates."""

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_ALLY_UPDATE_RECEIVED,
                self._async_update_callback,
            )
        )

    @callback
    def _async_update_callback(self):
        """Update and write state."""

        if (
            self._latest_write_time is None
            or (datetime.utcnow() - self._latest_write_time).total_seconds()
            >= self._skipdelayafterwrite
        ):
            _LOGGER.debug("Loading new switch data for device %s", self._device_id)
            self._device = self._ally.devices[self._device_id]
            self._async_update_data()
        else:
            _LOGGER.debug("Skip update: %s, %s", self._device_id, self._type)
        self.async_write_ha_state()

    def update_ui(self, new_state: bool):
        """Update UI."""
        self._latest_write_time = datetime.utcnow()
        self._attr_is_on = new_state
        self.async_write_ha_state()

    @callback
    def _async_update_data(self):
        """Virtual function. Override in derived class to define update method."""
        raise NotImplementedError()


class AllyGenericSwitch(AllyBaseSwitch):
    """Generic switch: description.key must be the name of the ally attribute."""

    def __init__(
        self, ally, name, device_id, description: SwitchEntityDescription, model
    ):
        """Initialize Ally generic switch."""
        self._ally_attr = description.key
        super().__init__(ally, name, device_id, description, model, 2)
        self._async_update_data()

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self._ally.send_commands(self._device_id, [(self._ally_attr, True)], False)
        super().update_ui(True)

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        self._ally.send_commands(self._device_id, [(self._ally_attr, False)], False)
        super().update_ui(False)

    @callback
    def _async_update_data(self):
        """Load data."""
        self._attr_available = self._ally_attr in self._device
        if self._attr_available:
            self._attr_is_on = self._device[self._ally_attr]


# class AllyOpenWindowDetectionSwitch(AllyBaseSwitch):

#     def __init__(self, ally, name, device_id, description: SwitchEntityDescription, model):
#         super().__init__(ally, name, device_id, description, model, 2)
#         self._async_update_data()

#     def turn_on(self, **kwargs):
#         """Turn the switch on."""
#         self._ally.send_commands(self._device_id, [("window_toggle", True)], False)
#         super().update_ui(True)

#     def turn_off(self, **kwargs):
#         """Turn the switch off."""
#         self._ally.send_commands(self._device_id, [("window_toggle", False)], False)
#         super().update_ui(False)

#     @callback
#     def _async_update_data(self):
#         """Load data."""
#         self._attr_available = ("window_toggle" in self._device)
#         if self._attr_available:
#             self._attr_is_on = self._device["window_toggle"]
