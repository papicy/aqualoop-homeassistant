"""Diagnostics for the Aqualoop integration."""

from __future__ import annotations

from dataclasses import asdict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from . import AqualoopConfigEntry

TO_REDACT = {"mac", "device_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: AqualoopConfigEntry
) -> dict:
    """Return redacted device and current state diagnostics."""
    data = entry.runtime_data
    return {
        "device": async_redact_data(asdict(data.info), TO_REDACT),
        "state": async_redact_data(asdict(data.coordinator.data), TO_REDACT),
    }
