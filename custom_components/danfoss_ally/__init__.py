"""Adds support for Danfoss Ally Gateway."""
import asyncio
from datetime import timedelta
import logging
import voluptuous as vol

from homeassistant.components.climate.const import PRESET_AWAY, PRESET_HOME
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import Throttle
from pydanfossally import DanfossAlly

from .const import (
    CONF_KEY,
    CONF_SECRET,
    DATA,
    DOMAIN,
    SIGNAL_ALLY_UPDATE_RECEIVED,
    UPDATE_LISTENER,
    UPDATE_TRACK,
)

_LOGGER = logging.getLogger(__name__)

ALLY_COMPONENTS = ["binary_sensor", "climate", "sensor"]

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=10)
SCAN_INTERVAL = 15

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            cv.ensure_list,
            [
                {
                    vol.Required(CONF_KEY): cv.string,
                    vol.Required(CONF_SECRET): cv.string,
                }
            ],
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Danfoss Ally component."""

    hass.data.setdefault(DOMAIN, {})

    if DOMAIN not in config:
        return True

    for conf in config[DOMAIN]:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=conf,
            )
        )

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Danfoss Ally from a config entry."""

    key = entry.data[CONF_KEY]
    secret = entry.data[CONF_SECRET]

    allyconnector = AllyConnector(hass, key, secret)
    try:
        await hass.async_add_executor_job(allyconnector.setup)
    except TimeoutError:
        _LOGGER.error("Timeout connecting to Danfoss Ally")
        raise ConfigEntryNotReady
    except:
        _LOGGER.error(
            "Something went horrible wrong when communicating with Danfoss Ally"
        )
        return False
    
    await hass.async_add_executor_job(allyconnector.update)
    
    update_track = async_track_time_interval(
        hass,
        lambda now: allyconnector.update(),
        timedelta(seconds=SCAN_INTERVAL),
    )

    update_listener = entry.add_update_listener(_async_update_listener)
    
    hass.data[DOMAIN][entry.entry_id] = {
        DATA: allyconnector,
        UPDATE_TRACK: update_track,
        UPDATE_LISTENER: update_listener,
    }

    for component in ALLY_COMPONENTS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True

async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
    
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in ALLY_COMPONENTS
            ]
        )
    )

    hass.data[DOMAIN][entry.entry_id][UPDATE_TRACK]()
    hass.data[DOMAIN][entry.entry_id][UPDATE_LISTENER]()

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class AllyConnector:
    """An object to store the Danfoss Ally data."""

    def __init__(self, hass, key, secret):
        """Initialize Danfoss Ally Connector."""
        self.hass = hass
        self._key = key
        self._secret = secret
        self.ally = DanfossAlly()

    def setup(self):
        auth = self.ally.initialize(
            self._key,
            self._secret
        )

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self, now=None):
        _LOGGER.debug("Updating Danfoss Ally devices")
        _LOGGER.debug("Token: %s", self.ally._token)
        self.ally.getDeviceList()
        for device in self.ally.devices:
            _LOGGER.debug(
                "%s: %s",
                device,
                self.ally.devices[device]
            )
        dispatcher_send(self.hass, SIGNAL_ALLY_UPDATE_RECEIVED)

    @property
    def devices(self):
        """Return device list from API."""
        return self.ally.devices

    def setTemperature(self, device_id: str, temperature: float):
        """Set temperature for device_id."""
        self.ally.setTemperature(device_id, temperature)