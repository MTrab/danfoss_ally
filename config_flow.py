"""Config flow for Tado integration."""
import logging

import requests.exceptions
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.core import callback
from pydanfossally import DanfossAlly

from .const import CONF_KEY, CONF_SECRET, UNIQUE_ID
from .const import DOMAIN  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_KEY): str, vol.Required(CONF_SECRET): str}
)


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """

    #_LOGGER.warning("Danfoss Ally creds: %s %s",data[CONF_KEY], data[CONF_SECRET])        
    ally = DanfossAlly()
    auth = await ally.initialize(data[CONF_KEY], data[CONF_SECRET])

    if not auth:
        raise InvalidAuth

    #_LOGGER.warning("Adding Danfoss Ally")        
    # try:
    #     ally = await hass.async_add_executor_job(
    #         DanfossAlly
    #     )
    #     ally = await hass.async_add_executor_job(
    #         ally.initialize,
    #         data[CONF_KEY],
    #         data[CONF_SECRET]
    #     )
    # except KeyError as ex:
    #     raise InvalidAuth from ex
    # except RuntimeError as ex:
    #     raise CannotConnect from ex
    # except requests.exceptions.HTTPError as ex:
    #     if ex.response.status_code > 400 and ex.response.status_code < 500:
    #         raise InvalidAuth from ex
    #     raise CannotConnect from ex

    # if "homes" not in tado_me or len(tado_me["homes"]) == 0:
    #     raise NoHomes

    # #home = tado_me["homes"][0]
    # #unique_id = str(home["id"])
    # #name = home["name"]
    #unique_id = "allytest123"
    # name = "Ally Test"

    # return {"title": name, UNIQUE_ID: unique_id}
    return {"title": f"Danfoss Ally"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Danfoss Ally."""

    VERSION = 1
    
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                #metering_point = user_input["metering_point"]
                info = f"Danfoss Ally"
                return self.async_create_entry(title=info, data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""