"""Local Mongoose OS RPC client for the Aqualoop controller."""

from __future__ import annotations

import asyncio
import json
import math
from dataclasses import dataclass
from typing import Any

import aiohttp

TIMEOUT = aiohttp.ClientTimeout(total=15)
TRANSPORT_RETRIES = 1
RETRY_DELAY_SECONDS = 0.25


class AqualoopError(Exception):
    """Communication or device error."""


class AqualoopNotPatchedError(AqualoopError):
    """Device does not expose the Heater.* RPC handlers."""


@dataclass
class DeviceInfo:
    mac: str
    device_id: str
    fw_version: str
    app: str


@dataclass
class HeaterState:
    temperature: float | None
    setpoint: int
    heating: bool
    error: bool
    ready: bool
    min_setpoint: int
    max_setpoint: int
    schedules: list[dict[str, Any]]

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> HeaterState:
        if not isinstance(data, dict):
            raise ValueError("heater response must be an object")

        required = {"ready", "error", "temperature", "setpoint", "heating"}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"heater response missing {', '.join(sorted(missing))}")

        ready = _require_bool(data["ready"], "ready")
        error = _require_bool(data["error"], "error")
        temp = _require_number(data["temperature"], "temperature")
        schedules = data.get("schedules")
        if schedules is None:
            schedules = []
        if not isinstance(schedules, list) or not all(
            isinstance(schedule, dict) for schedule in schedules
        ):
            raise ValueError("heater schedules must be a list")

        setpoint = _require_int(data["setpoint"], "setpoint")
        min_setpoint = _require_int(data.get("min_setpoint", 30), "min_setpoint")
        max_setpoint = _require_int(data.get("max_setpoint", 72), "max_setpoint")
        if min_setpoint > max_setpoint:
            raise ValueError("heater setpoint limits are invalid")
        if setpoint != 0 and not min_setpoint <= setpoint <= max_setpoint:
            raise ValueError("heater setpoint is outside the reported limits")

        return cls(
            temperature=(
                temp if ready and not error else None
            ),
            setpoint=setpoint,
            heating=_require_bool(data["heating"], "heating"),
            error=error,
            ready=ready,
            min_setpoint=min_setpoint,
            max_setpoint=max_setpoint,
            schedules=schedules,
        )


def _require_bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"heater {name} must be a boolean")
    return value


def _require_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"heater {name} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"heater {name} must be finite")
    return number


def _require_int(value: Any, name: str) -> int:
    number = _require_number(value, name)
    if not number.is_integer():
        raise ValueError(f"heater {name} must be an integer")
    return int(number)


class AqualoopClient:
    """Talks to http://<host>/rpc/<method>."""

    def __init__(self, host: str, session: aiohttp.ClientSession) -> None:
        self._base = f"http://{host}/rpc"
        self._session = session
        self._lock = asyncio.Lock()

    async def _call(
        self, method: str, params: dict[str, Any] | None = None, raw: bool = False
    ) -> Any:
        async with self._lock:
            for attempt in range(TRANSPORT_RETRIES + 1):
                try:
                    async with self._session.post(
                        f"{self._base}/{method}", json=params or {}, timeout=TIMEOUT
                    ) as resp:
                        text = await resp.text()
                        if resp.status == 404:
                            raise AqualoopNotPatchedError(f"{method} not available")
                        if resp.status != 200:
                            raise AqualoopError(
                                f"{method} failed ({resp.status}): {text.strip()}"
                            )
                except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                    if attempt < TRANSPORT_RETRIES:
                        await asyncio.sleep(RETRY_DELAY_SECONDS)
                        continue
                    message = str(err) or "request timed out"
                    raise AqualoopError(f"{method}: {message}") from err
                break
        if raw:
            return text.strip().strip('"')
        try:
            return json.loads(text)
        except ValueError as err:
            raise AqualoopError(f"{method}: invalid response") from err

    async def get_info(self) -> DeviceInfo:
        data = await self._call("Sys.GetInfo")
        device_id = await self._call("Config.Get", {"key": "device.id"}, raw=True)
        return DeviceInfo(
            mac=str(data.get("mac", "")),
            device_id=str(device_id or ""),
            fw_version=str(data.get("fw_version", "")),
            app=str(data.get("app", "")),
        )

    async def get_state(self) -> HeaterState:
        return self._parse_heater_state(await self._call("Heater.Get"))

    async def set_setpoint(self, setpoint: int) -> HeaterState:
        return self._parse_heater_state(
            await self._call("Heater.Set", {"setpoint": int(setpoint)})
        )

    @staticmethod
    def _parse_heater_state(data: Any) -> HeaterState:
        if not isinstance(data, dict):
            raise AqualoopError("heater response must be an object")

        device_error = data.get("error")
        if (
            isinstance(device_error, (int, float))
            and not isinstance(device_error, bool)
            and device_error != 0
        ):
            message = data.get("message") or "device rejected the request"
            raise AqualoopError(str(message))

        try:
            return HeaterState.from_json(data)
        except (TypeError, ValueError) as err:
            raise AqualoopError("invalid heater response") from err
