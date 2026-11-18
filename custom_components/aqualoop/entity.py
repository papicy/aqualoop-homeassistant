"""Base entity for Aqualoop."""

from __future__ import annotations

from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
    format_mac,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AqualoopConfigEntry, AqualoopCoordinator
from .const import DOMAIN, MANUFACTURER


class AqualoopEntity(CoordinatorEntity[AqualoopCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, entry: AqualoopConfigEntry, key: str) -> None:
        super().__init__(entry.runtime_data.coordinator)
        info = entry.runtime_data.info
        self._attr_unique_id = f"{entry.unique_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            connections={(CONNECTION_NETWORK_MAC, format_mac(info.mac))},
            manufacturer=MANUFACTURER,
            model=info.app,
            name=f"Aqualoop {info.device_id}".strip(),
            sw_version=info.fw_version,
        )
