"""Diagnostics for the Aqualoop integration."""

from __future__ import annotations

from dataclasses import asdict

from homeassistant.core import HomeAssistant

from . import AqualoopConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: AqualoopConfigEntry
) -> dict:
    """Return device and current state diagnostics without credentials."""
    data = entry.runtime_data
    return {
        "device": asdict(data.info),
        "state": asdict(data.coordinator.data),
    }
