"""Support for Ally select."""
from __future__ import annotations

import logging
from datetime import datetime
from enum import IntEnum

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory

from .const import DATA, DOMAIN, SIGNAL_ALLY_UPDATE_RECEIVED
from .entity import AllyDeviceEntity

_LOGGER = logging.getLogger(__name__)


class AllySelectType(IntEnum):
    """Supported sensor types."""


options_hcs = {"Quick (5min)": 1, "Moderate (30min)": 5, "Slow (80min)": 10}

SELECTS = [
    SelectEntityDescription(
        key="ctrl_alg",
        entity_category=EntityCategory.CONFIG,
        name="{} Heating Control Scaling",
        device_class=None,
        options=list(options_hcs.keys()),
        icon="mdi:car-traction-control",
        entity_registry_enabled_default=False,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up the Ally select platform."""
    _LOGGER.debug("Setting up Danfoss Ally select entities")
    ally = hass.data[DOMAIN][entry.entry_id][DATA]
    entities = []

    for device in ally.devices:
        for sel in SELECTS:
            if (
                sel.key
                in [
                    "ctrl_alg",
                ]
                and sel.key in ally.devices[device]
            ):
                _LOGGER.debug(
                    "Found select for setting: %s", ally.devices[device]["name"]
                )
                entities.extend(
                    [
                        AllyHcsSelect(
                            ally,
                            ally.devices[device]["name"],
                            device,
                            sel,
                            ally.devices[device]["model"],
                            options_hcs,
                        )
                    ]
                )

    if entities:
        async_add_entities(entities, True)


class AllyBaseSelect(AllyDeviceEntity, SelectEntity):
    """Base class of select"""

    def __init__(
        self,
        ally,
        name,
        device_id,
        description: SelectEntityDescription,
        model,
        options,
        skipdelayafterwrite=2,
    ):
        """Initialize Ally select."""
        self.entity_description = description
        self._ally = ally
        self._device = ally.devices[device_id]
        self._device_id = device_id
        self._name = name
        self._options = options
        self._type = description.name.lower()
        self._latest_write_time = None
        self._skipdelayafterwrite = skipdelayafterwrite

        super().__init__(name, device_id, self._type, model)

        _LOGGER.debug("Device_id: %s --- Device: %s", self._device_id, self._device)

        self._attr_current_option = None
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
            _LOGGER.debug("Loading new select data for device %s", self._device_id)
            self._device = self._ally.devices[self._device_id]
            self._async_update_data()
        else:
            _LOGGER.debug("Skip update: %s, %s", self._device_id, self._type)
        self.schedule_update_ha_state()

    def update_ui(self, option: str):
        """Update UI."""
        self._latest_write_time = datetime.utcnow()
        self._attr_current_option = option
        self.schedule_update_ha_state()

    @callback
    def _async_update_data(self):
        """Virtual function. Override in derived class to define update method."""
        raise NotImplementedError()


# class AllyGenericSelect(AllyBaseSelect):
#     """Generic select: description.key must be the name of the ally attribute."""

#     def __init__(
#         self,
#         ally,
#         name,
#         device_id,
#         description: SelectEntityDescription,
#         model,
#         options,
#     ):
#         """Initialize Ally generic select."""
#         self._ally_attr = description.key
#         super().__init__(ally, name, device_id, description, model, options, 2)
#         self._async_update_data()

#     def select_option(self, option: str) -> None:
#         """Set selected option."""
#         value = self._options[option]
#         self._ally.send_commands(self._device_id, [(self._ally_attr, value)], False)
#         super().update_ui(option)

#     @callback
#     def _async_update_data(self):
#         """Load data."""
#         self._attr_available = self._ally_attr in self._device
#         if self._attr_available:
#             value = self._device[self._ally_attr]
#             option = None
#             for item in self._options:
#                 if value == self._options[item]:
#                     option = item
#             self._attr_current_option = option


class AllyHcsSelect(AllyBaseSelect):
    """Select for Heating Control Scaling (lower 4 bits only): description.key must be the name of the ally attribute."""

    def __init__(
        self,
        ally,
        name,
        device_id,
        description: SelectEntityDescription,
        model,
        options,
    ):
        """Initialize Ally generic select."""
        self._ally_attr = description.key
        super().__init__(ally, name, device_id, description, model, options, 2)
        self._async_update_data()

    def select_option(self, option: str) -> None:
        """Set selected option, lower 4 bits only, keep other bits."""

        value = self._options[option]
        other_bits = int(self._device[self._ally_attr]) & 0xF0  # It is an uint8
        value = (int(value) & 0x0F) | other_bits

        self._ally.send_commands(self._device_id, [(self._ally_attr, value)], False)
        super().update_ui(option)

    @callback
    def _async_update_data(self):
        """Load data."""
        self._attr_available = self._ally_attr in self._device
        if self._attr_available:
            value = int(self._device[self._ally_attr]) & 0x0F
            option = None
            for item in self._options:
                if value >= self._options[item]:
                    option = item
            self._attr_current_option = option
