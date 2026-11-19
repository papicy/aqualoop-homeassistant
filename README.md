# Aqualoop Water Heater for Home Assistant

Local control of an Aqualoop controller (ESP32 / Mongoose OS, `aqualoop-controller` fw 1.6) with no cloud dependency.

The integration communicates over the local network. The controller's original AWS cloud connection remains enabled.

## How it works

The stock firmware sends temperature and setpoint only to AWS IoT. `device/install_patch.py` adds two local RPC methods to the controller's `init.js`:

| Method | Body | Returns |
|---|---|---|
| `POST /rpc/Heater.Get` | `{}` | `temperature`, `setpoint`, `heating`, `error`, `ready`, `min_setpoint`, `max_setpoint`, `schedules` |
| `POST /rpc/Heater.Set` | `{"setpoint": N}` | Same as `Heater.Get`. `0` means off, otherwise 30–72 °C. |

`Heater.Set` uses the same state-machine path as the physical button, so the vendor app and cloud shadow stay in sync. The controller heats to the target and then switches itself off, resetting the setpoint to 0.

## 1. Patch the controller

Replace `192.0.2.1` with your controller's address:

```
cd device
python install_patch.py 192.0.2.1            # install (backs up original first) + reboot
python install_patch.py 192.0.2.1 --restore  # put the original back
```

Keep the original firmware backup safe. It remains local and is excluded from Git.

Re-run the installer if a vendor OTA update replaces `init.js`. The integration reports `not_patched` when the handlers are missing.

## 2. Install the integration

Copy `custom_components/aqualoop` to `<config>/custom_components/aqualoop`.

The included `brand` folder supplies the integration icon on Home Assistant 2026.3 and later.
For an existing installation, create `brand` inside the `aqualoop` integration folder and copy both images into it:

```text
custom_components\
  aqualoop\
    brand\
      icon.png       (256 x 256)
      icon@2x.png    (512 x 512)
```

Keep these exact filenames. Restart Home Assistant after copying the files; no configuration changes are needed.

### Home Assistant 2026.11 and newer

The former HACS integration is now built into Home Assistant as **Marketplace**.
Open **Settings → Marketplace**, add this GitHub repository as a custom
**Integration**, and install **Aqualoop Water Heater**. The repository must be
public and have a `hacs.json` file at its root.

### Home Assistant 2026.10 and older

Use HACS and add this repository as a custom **Integration** repository.

After installation, restart Home Assistant if requested. Then go to
**Settings → Devices & services → Add integration → Aqualoop** and enter the
IP address.

## Entities

- `water_heater`: current temperature, target temperature, and on/off (operation `electric`/`off`). Turning it on uses the last target (default 60 °C).
- `sensor`: Water temperature, Active setpoint
- `binary_sensor`: Heating, Sensor error, Ready (diagnostic)

The device is polled every 15 s. It reads its own temperature sensor about once a minute.
The water heater is unavailable while the controller reports that it is not ready.

Home Assistant diagnostics include the controller identity and current heater state;
credentials are not included.

## Security note

The controller's RPC API on port 80 is unauthenticated. Anyone on your LAN can read its Wi-Fi password and AWS key (`Config.Get`/`FS.Get`) and can change its files. This was true before the patch. Keep it on a trusted network or VLAN.

## Tests

```
pip install pytest-homeassistant-custom-component
pytest
```
