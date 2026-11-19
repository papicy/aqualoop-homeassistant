"""Config flow for Aqualoop."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithConfigEntry,
)
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    SelectorMode,
)

from .api import AqualoopClient, AqualoopError, AqualoopNotPatchedError
from .const import (
    CONF_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL_SECONDS,
    MIN_SCAN_INTERVAL_SECONDS,
    SCAN_INTERVAL_SECONDS,
)


class AqualoopConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            if not host:
                errors["base"] = "invalid_host"
            else:
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
                        normalized_mac = info.mac.replace(":", "").replace("-", "")
                        if not re.fullmatch(r"[0-9a-fA-F]{12}", normalized_mac):
                            errors["base"] = "invalid_device"
                            return self.async_show_form(
                                step_id="user",
                                data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
                                errors=errors,
                            )
                        unique_id = format_mac(normalized_mac)
                        await self.async_set_unique_id(unique_id)
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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AqualoopOptionsFlow(config_entry)


class AqualoopOptionsFlow(OptionsFlowWithConfigEntry):
    """Configure polling for an Aqualoop controller."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])}
            )

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, SCAN_INTERVAL_SECONDS
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=current
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL_SECONDS,
                            max=MAX_SCAN_INTERVAL_SECONDS,
                            step=1,
                            mode=SelectorMode.BOX,
                        )
                    )
                }
            ),
        )
