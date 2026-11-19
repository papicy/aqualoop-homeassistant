"""Tests for the Aqualoop integration (run with pytest-homeassistant-custom-component)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.components.water_heater import (
    ATTR_OPERATION_MODE,
    DOMAIN as WH_DOMAIN,
    SERVICE_SET_OPERATION_MODE,
    SERVICE_SET_TEMPERATURE,
    STATE_ELECTRIC,
)
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE, CONF_HOST, STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.core import State
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aqualoop.api import (
    AqualoopError,
    AqualoopNotPatchedError,
    DeviceInfo,
    HeaterState,
)
from custom_components.aqualoop.const import DOMAIN

INFO = DeviceInfo(mac="AA0000000001", device_id="AQL00000001", fw_version="1.6", app="aqualoop-controller")
CLIENT = "custom_components.aqualoop.api.AqualoopClient"
WH = "water_heater.aqualoop_aql00000001"


def state(**kw) -> HeaterState:
    base = {"temperature": 53, "setpoint": 0, "heating": False, "error": False,
            "ready": True, "min_setpoint": 30, "max_setpoint": 72, "schedules": []}
    base.update(kw)
    return HeaterState.from_json(base)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


class FakeDevice:
    """Mimics the patched firmware's Heater.Set semantics."""

    def __init__(self) -> None:
        self.s = state()
        self.calls: list[int] = []

    async def get_info(self):
        return INFO

    async def get_state(self):
        return self.s

    async def set_setpoint(self, sp: int):
        self.calls.append(sp)
        heating = sp > self.s.temperature
        self.s = state(temperature=self.s.temperature, setpoint=sp, heating=heating)
        return self.s


@pytest.fixture
def device():
    dev = FakeDevice()
    with patch(f"{CLIENT}.get_info", side_effect=dev.get_info), \
         patch(f"{CLIENT}.get_state", side_effect=dev.get_state), \
         patch(f"{CLIENT}.set_setpoint", side_effect=dev.set_setpoint):
        yield dev


async def setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: "192.0.2.1"}, unique_id="aa:00:00:00:00:01")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_config_flow_creates_entry(hass: HomeAssistant, device) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: "192.0.2.1"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Aqualoop AQL00000001"
    assert result["result"].unique_id == "aa:00:00:00:00:01"


@pytest.mark.parametrize(
    ("exc", "err"),
    [(AqualoopNotPatchedError("x"), "not_patched"), (AqualoopError("x"), "cannot_connect")],
)
async def test_config_flow_errors(hass: HomeAssistant, device, exc, err) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    with patch(f"{CLIENT}.get_state", side_effect=exc):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: "192.0.2.1"})
    assert result["errors"] == {"base": err}


async def test_config_flow_rejects_invalid_device_identity(
    hass: HomeAssistant, device
) -> None:
    with patch(
        f"{CLIENT}.get_info",
        return_value=DeviceInfo(
            mac="not-a-mac",
            device_id="AQL00000001",
            fw_version="1.6",
            app="aqualoop-controller",
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: "192.0.2.1"}
        )

    assert result["errors"] == {"base": "invalid_device"}


async def test_entities_and_control(hass: HomeAssistant, device) -> None:
    await setup(hass)
    st = hass.states.get(WH)
    assert st.state == STATE_OFF
    assert st.attributes["current_temperature"] == 53
    assert hass.states.get("sensor.aqualoop_aql00000001_water_temperature").state == "53.0"

    await hass.services.async_call(
        WH_DOMAIN, SERVICE_SET_TEMPERATURE, {ATTR_ENTITY_ID: WH, ATTR_TEMPERATURE: 58}, blocking=True
    )
    st = hass.states.get(WH)
    assert device.calls[-1] == 58
    assert st.state == STATE_ELECTRIC
    assert st.attributes["temperature"] == 58
    assert hass.states.get("binary_sensor.aqualoop_aql00000001_heating").state == "on"

    await hass.services.async_call(
        WH_DOMAIN, SERVICE_SET_OPERATION_MODE, {ATTR_ENTITY_ID: WH, ATTR_OPERATION_MODE: STATE_OFF}, blocking=True
    )
    assert device.calls[-1] == 0
    st = hass.states.get(WH)
    assert st.state == STATE_OFF
    assert st.attributes["temperature"] == 58

    await hass.services.async_call(
        WH_DOMAIN, SERVICE_SET_OPERATION_MODE, {ATTR_ENTITY_ID: WH, ATTR_OPERATION_MODE: STATE_ELECTRIC}, blocking=True
    )
    assert device.calls[-1] == 58


async def test_entities_have_relevant_icons(hass: HomeAssistant, device) -> None:
    await setup(hass)

    expected_icons = {
        WH: "mdi:water-boiler",
        "sensor.aqualoop_aql00000001_water_temperature": "mdi:thermometer",
        "sensor.aqualoop_aql00000001_setpoint": "mdi:target",
        "binary_sensor.aqualoop_aql00000001_heating": "mdi:fire",
        "binary_sensor.aqualoop_aql00000001_sensor_error": "mdi:alert-circle",
        "binary_sensor.aqualoop_aql00000001_ready": "mdi:check-circle",
    }

    for entity_id, icon in expected_icons.items():
        assert hass.states[entity_id].attributes["icon"] == icon


async def test_device_error_surfaces(hass: HomeAssistant, device) -> None:
    await setup(hass)
    with patch(f"{CLIENT}.set_setpoint", side_effect=AqualoopError("boom")), pytest.raises(HomeAssistantError):
        await hass.services.async_call(WH_DOMAIN, "turn_on", {ATTR_ENTITY_ID: WH}, blocking=True)


async def test_rpc_device_error_payload_surfaces() -> None:
    from custom_components.aqualoop.api import AqualoopClient

    client = AqualoopClient("192.0.2.1", None)
    with patch.object(
        client,
        "_call",
        new=AsyncMock(return_value={"error": -1, "message": "heater sensor error"}),
    ), pytest.raises(AqualoopError, match="heater sensor error"):
        await client.set_setpoint(60)


async def test_rpc_malformed_payload_surfaces() -> None:
    from custom_components.aqualoop.api import AqualoopClient

    client = AqualoopClient("192.0.2.1", None)
    with patch.object(client, "_call", new=AsyncMock(return_value={"setpoint": "bad"})):
        with pytest.raises(AqualoopError, match="invalid heater response"):
            await client.get_state()


async def test_last_target_is_restored(hass: HomeAssistant, device) -> None:
    with patch(
        "custom_components.aqualoop.water_heater.AqualoopWaterHeater.async_get_last_state",
        new=AsyncMock(return_value=State(WH, STATE_OFF, {ATTR_TEMPERATURE: 64})),
    ):
        await setup(hass)

    await hass.services.async_call(
        WH_DOMAIN, "turn_on", {ATTR_ENTITY_ID: WH}, blocking=True
    )
    assert device.calls[-1] == 64


async def test_sensor_fault_marks_unavailable(hass: HomeAssistant, device) -> None:
    device.s = state(temperature=-1, error=True)
    await setup(hass)
    assert hass.states.get(WH).state == "unavailable"
    assert hass.states.get("binary_sensor.aqualoop_aql00000001_sensor_error").state == "on"


async def test_not_ready_marks_water_heater_unavailable(hass: HomeAssistant, device) -> None:
    device.s = state(temperature=120, ready=False)
    await setup(hass)
    assert hass.states.get(WH).state == "unavailable"
    assert hass.states.get("binary_sensor.aqualoop_aql00000001_ready").state == "off"
