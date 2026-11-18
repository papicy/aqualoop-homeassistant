"""Sensors for Aqualoop."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AqualoopConfigEntry
from .entity import AqualoopEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: AqualoopConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([AqualoopTemperature(entry), AqualoopSetpoint(entry)])


class AqualoopTemperature(AqualoopEntity, SensorEntity):
    _attr_translation_key = "water_temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, entry: AqualoopConfigEntry) -> None:
        super().__init__(entry, "temperature")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.temperature


class AqualoopSetpoint(AqualoopEntity, SensorEntity):
    """Active setpoint; 0 means idle."""

    _attr_translation_key = "setpoint"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, entry: AqualoopConfigEntry) -> None:
        super().__init__(entry, "setpoint")

    @property
    def native_value(self) -> int:
        return self.coordinator.data.setpoint
