"""The Aqualoop water heater integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AqualoopClient, AqualoopError, DeviceInfo, HeaterState
from .const import CONF_SCAN_INTERVAL, DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.WATER_HEATER, Platform.SENSOR, Platform.BINARY_SENSOR]


class AqualoopCoordinator(DataUpdateCoordinator[HeaterState]):
    """Polls Heater.Get."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: AqualoopClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, SCAN_INTERVAL_SECONDS)
            ),
        )
        self.client = client

    async def _async_update_data(self) -> HeaterState:
        try:
            return await self.client.get_state()
        except AqualoopError as err:
            raise UpdateFailed(str(err)) from err

    async def async_set_setpoint(self, setpoint: int) -> None:
        try:
            state = await self.client.set_setpoint(setpoint)
        except AqualoopError as err:
            raise HomeAssistantError(f"Aqualoop: {err}") from err
        self.async_set_updated_data(state)


@dataclass
class AqualoopData:
    coordinator: AqualoopCoordinator
    info: DeviceInfo


type AqualoopConfigEntry = ConfigEntry[AqualoopData]


async def async_setup_entry(hass: HomeAssistant, entry: AqualoopConfigEntry) -> bool:
    client = AqualoopClient(entry.data[CONF_HOST], async_get_clientsession(hass))
    try:
        info = await client.get_info()
    except AqualoopError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = AqualoopCoordinator(hass, entry, client)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = AqualoopData(coordinator, info)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AqualoopConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(hass: HomeAssistant, entry: AqualoopConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
