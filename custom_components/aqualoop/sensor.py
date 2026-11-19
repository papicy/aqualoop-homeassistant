"""Sensors for Aqualoop."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AqualoopConfigEntry
from .const import HEATER_POWER_W
from .entity import AqualoopEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: AqualoopConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(
        [
            AqualoopTemperature(entry),
            AqualoopSetpoint(entry),
            AqualoopPower(entry),
            AqualoopScheduleCount(entry),
        ]
    )


class AqualoopTemperature(AqualoopEntity, SensorEntity):
    _attr_translation_key = "water_temperature"
    _attr_icon = "mdi:thermometer"
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
    _attr_icon = "mdi:target"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, entry: AqualoopConfigEntry) -> None:
        super().__init__(entry, "setpoint")

    @property
    def native_value(self) -> int:
        return self.coordinator.data.setpoint


class AqualoopPower(AqualoopEntity, SensorEntity):
    """Estimate the heater's instantaneous electrical power draw."""

    _attr_translation_key = "power"
    _attr_icon = "mdi:flash"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(self, entry: AqualoopConfigEntry) -> None:
        super().__init__(entry, "power")

    @property
    def native_value(self) -> int:
        return HEATER_POWER_W if self.coordinator.data.heating else 0


class AqualoopScheduleCount(AqualoopEntity, SensorEntity):
    """Expose the controller's configured schedule count."""

    _attr_translation_key = "schedule_count"
    _attr_icon = "mdi:calendar-clock"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: AqualoopConfigEntry) -> None:
        super().__init__(entry, "schedule_count")

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.schedules)

    @property
    def extra_state_attributes(self) -> dict[str, list[dict]]:
        return {"schedules": self.coordinator.data.schedules}
