# Aqualoop Water Heater for Home Assistant

This integration lets Home Assistant control an Aqualoop water heater over your local network. It does not need the cloud service. The controller's existing AWS connection stays enabled.

## What you need

- An Aqualoop controller running `aqualoop-controller` firmware 1.6.
- The controller's IP address.
- Access to your Home Assistant configuration folder.

## How it works

The original firmware does not provide the local controls that Home Assistant needs. The patch in `device/install_patch.py` adds these two local RPC methods to the controller:

| Method | Body | Returns |
|---|---|---|
| `POST /rpc/Heater.Get` | `{}` | `temperature`, `setpoint`, `heating`, `error`, `ready`, `min_setpoint`, `max_setpoint`, `schedules` |
| `POST /rpc/Heater.Set` | `{"setpoint": N}` | Same as `Heater.Get`. `0` means off, otherwise 30–72 °C. |

`Heater.Set` uses the same state-machine path as the physical button, so the vendor app and cloud shadow stay in sync. The controller heats to the target and then switches itself off, resetting the setpoint to 0.

## 1. Patch the controller

Run the patch from the repository's `device` folder. Replace `192.0.2.1` with the controller's IP address:

```
cd device
python install_patch.py 192.0.2.1
```

The installer saves a copy of the original file and reboots the controller. Keep that backup safe. It stays on your computer and is not added to Git.

To restore the original file:

```
python install_patch.py 192.0.2.1 --restore
```

Run the installer again if a vendor update replaces `init.js`. Home Assistant shows `not_patched` when the controller has not been patched.

## 2. Install the integration in Home Assistant

The HACS Marketplace is the recommended installation method. Use the GitHub or manual method only when the Marketplace option is unavailable.

### Option A: Install from the HACS Marketplace

**Recommended.** Use this method when **Aqualoop Water Heater** is listed in the HACS Marketplace:

1. Open **HACS** in Home Assistant.
2. Open **Integrations**.
3. Search for **Aqualoop Water Heater**.
4. Select it and choose **Download**.

Restart Home Assistant after the download finishes.

### Option B: Install from this GitHub repository

Use this method if the integration is not yet in the HACS Marketplace:

1. Open **HACS** in Home Assistant.
2. Open **Integrations**.
3. Open the menu in the top-right and choose **Custom repositories**.
4. Enter `https://github.com/papicy/aqualoop-homeassistant`.
5. Select **Integration** as the repository type and choose **Add**.
6. Find **Aqualoop** in HACS and select **Download**.

Restart Home Assistant after the download finishes.

### Option C: Copy the integration manually

Copy the `custom_components/aqualoop` folder from this repository to:

```text
<config>/custom_components/aqualoop
```

For example, the final folder should contain:

```text
custom_components\
  aqualoop\
    __init__.py
    config_flow.py
    manifest.json
```

The repository already includes the `brand` folder and its integration icons. Keep that folder when copying the integration. For an older installation, add these files if they are missing:

```text
custom_components\
  aqualoop\
    brand\
      icon.png
      icon@2x.png
```

Restart Home Assistant after copying the files. No YAML configuration is needed.

## 3. Add the integration

In Home Assistant, go to **Settings → Devices & services → Add integration**, search for **Aqualoop**, and enter the controller's IP address.

## Entities

- `water_heater`: current temperature, target temperature, and on/off (operation `electric`/`off`). Turning it on uses the last target (default 60 °C).
- `sensor`: Water temperature, Active setpoint
- `binary_sensor`: Heating, Sensor error (diagnostic)

The device is polled every 15 s. It reads its own temperature sensor about once a minute.

## Security note

The controller's RPC API on port 80 is unauthenticated. Anyone on your LAN can read its Wi-Fi password and AWS key (`Config.Get`/`FS.Get`) and can change its files. This was true before the patch. Keep it on a trusted network or VLAN.

## Tests

```
pip install pytest-homeassistant-custom-component
pytest
```
