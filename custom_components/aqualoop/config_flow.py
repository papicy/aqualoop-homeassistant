"""Config flow for Aqualoop."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import format_mac

from .api import AqualoopClient, AqualoopError, AqualoopNotPatchedError
from .const import DOMAIN


class AqualoopConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            client = AqualoopClient(host, async_get_clientsession(self.hass))
            try:
                info = await client.get_info()
                await client.get_state()
            except AqualoopNotPatchedError:
                errors["base"] = "not_patched"
            except AqualoopError:
                errors["base"] = "cannot_connect"
            else:
                if info.app != "aqualoop-controller":
                    errors["base"] = "not_aqualoop"
                else:
                    await self.async_set_unique_id(format_mac(info.mac))
                    self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                    return self.async_create_entry(
                        title=f"Aqualoop {info.device_id}".strip(),
                        data={CONF_HOST: host},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
            errors=errors,
        )
