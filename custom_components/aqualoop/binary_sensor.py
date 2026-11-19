"""Binary sensors for Aqualoop."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AqualoopConfigEntry
from .entity import AqualoopEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: AqualoopConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(
        [AqualoopHeating(entry), AqualoopProblem(entry), AqualoopReady(entry)]
    )


class AqualoopHeating(AqualoopEntity, BinarySensorEntity):
    _attr_translation_key = "heating"
    _attr_icon = "mdi:fire"
    _attr_device_class = BinarySensorDeviceClass.HEAT

    def __init__(self, entry: AqualoopConfigEntry) -> None:
        super().__init__(entry, "heating")

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.heating


class AqualoopProblem(AqualoopEntity, BinarySensorEntity):
    _attr_translation_key = "sensor_error"
    _attr_icon = "mdi:alert-circle"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: AqualoopConfigEntry) -> None:
        super().__init__(entry, "sensor_error")

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.error


class AqualoopReady(AqualoopEntity, BinarySensorEntity):
    _attr_translation_key = "ready"
    _attr_icon = "mdi:check-circle"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: AqualoopConfigEntry) -> None:
        super().__init__(entry, "ready")

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.ready
