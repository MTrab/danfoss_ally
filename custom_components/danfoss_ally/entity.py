"""Base class for Danfoss Ally entity."""
from homeassistant.helpers.entity import Entity

from .const import DEFAULT_NAME, DOMAIN


class AllyDeviceEntity(Entity):
    """Base implementation for Ally device."""

    def __init__(self, name, device_id, device_type, model=None):
        """Initialize a Ally device."""
        super().__init__()
        self._type = device_type
        self._name = name
        self._device_id = device_id
        self._model = model

    @property
    def device_info(self):
        """Return the device_info of the device."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._name,
            "manufacturer": DEFAULT_NAME,
            "model": self._model,
        }

    @property
    def should_poll(self):
        """Do not poll."""
        return False
