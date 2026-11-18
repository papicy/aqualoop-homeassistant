"""Water heater entity for Aqualoop.

The controller works as "heat to target": once the water reaches the
setpoint it switches off and resets the setpoint to 0.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.water_heater import (
    STATE_ELECTRIC,
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.const import ATTR_TEMPERATURE, STATE_OFF, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AqualoopConfigEntry
from .const import DEFAULT_TARGET
from .entity import AqualoopEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: AqualoopConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([AqualoopWaterHeater(entry)])


class AqualoopWaterHeater(AqualoopEntity, WaterHeaterEntity):
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_precision = 1.0
    _attr_target_temperature_step = 1
    _attr_operation_list = [STATE_OFF, STATE_ELECTRIC]
    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE
        | WaterHeaterEntityFeature.OPERATION_MODE
        | WaterHeaterEntityFeature.ON_OFF
    )

    def __init__(self, entry: AqualoopConfigEntry) -> None:
        super().__init__(entry, "water_heater")
        self._last_target = DEFAULT_TARGET

    @property
    def min_temp(self) -> float:
        return self.coordinator.data.min_setpoint

    @property
    def max_temp(self) -> float:
        return self.coordinator.data.max_setpoint

    @property
    def current_temperature(self) -> float | None:
        return self.coordinator.data.temperature

    @property
    def target_temperature(self) -> float | None:
        sp = self.coordinator.data.setpoint
        return sp if sp > 0 else self._last_target

    @property
    def current_operation(self) -> str:
        return STATE_ELECTRIC if self.coordinator.data.heating else STATE_OFF

    @property
    def available(self) -> bool:
        return super().available and not self.coordinator.data.error

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data.setpoint > 0:
            self._last_target = self.coordinator.data.setpoint
        super()._handle_coordinator_update()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        self._last_target = int(round(temp))
        await self.coordinator.async_set_setpoint(self._last_target)

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        if operation_mode == STATE_OFF:
            await self.async_turn_off()
        else:
            await self.async_turn_on()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_setpoint(self._last_target)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_setpoint(0)
