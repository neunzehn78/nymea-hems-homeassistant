import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import DOMAIN, DEFAULT_PORT
from .nymea_client import NymeaClient, NymeaAuthError, NymeaConnectionError

_LOGGER = logging.getLogger(__name__)


async def _validate_connection(hass: HomeAssistant, data: dict) -> None:
    """
    Try to connect and authenticate.
    Raises NymeaConnectionError or NymeaAuthError on failure.
    """
    client = NymeaClient(
        data["host"],
        data["port"],
        data["username"],
        data["password"],
    )
    try:
        await client.authenticate()
    finally:
        await client.disconnect()


class NymeaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1

    async def async_step_user(self, user_input=None):

        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await _validate_connection(self.hass, user_input)
            except NymeaAuthError:
                errors["base"] = "invalid_auth"
            except NymeaConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Nymea config validation")
                errors["base"] = "unknown"
            else:
                # Prevent duplicate entries for the same host
                await self.async_set_unique_id(
                    f"{user_input['host']}:{user_input['port']}"
                )
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Nymea @ {user_input['host']}",
                    data=user_input,
                )

        schema = vol.Schema({
            vol.Required("host"): str,
            vol.Required("port", default=DEFAULT_PORT): int,
            vol.Required("username"): str,
            vol.Required("password"): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
