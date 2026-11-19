"""Install/restore the Home Assistant RPC patch on an Aqualoop controller.

Usage:
    python install_patch.py 192.0.2.1            # install patch + reboot
    python install_patch.py 192.0.2.1 --restore  # restore backup + reboot

Replace the example address with the controller's address.

Uses only the Python standard library. A byte-exact backup of the device's
original init.js is written next to this script as init.js.<device>.orig
before anything is changed.
"""

from __future__ import annotations

import argparse
import base64
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).parent
PATCH = (HERE / "init_ha_patch.js").read_text(encoding="utf-8")
MARKER = "/*---------- Local LAN API (Home Assistant) ------------*/"
CHUNK = 1500


def rpc(host: str, method: str, params: dict | None = None, timeout: int = 15):
    req = urllib.request.Request(
        f"http://{host}/rpc/{method}",
        data=json.dumps(params or {}).encode(),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode()
    try:
        return json.loads(body)
    except ValueError:
        return body.strip().strip('"')


def get_file(host: str, name: str) -> bytes:
    result = rpc(host, "FS.Get", {"filename": name, "len": 60000})
    if not isinstance(result, dict) or not isinstance(result.get("data"), str):
        raise SystemExit(f"FS.Get did not return file data for {name}.")
    try:
        return base64.b64decode(result["data"], validate=True)
    except ValueError as err:
        raise SystemExit(f"FS.Get returned invalid data for {name}.") from err


def put_file(host: str, name: str, data: bytes) -> None:
    for i in range(0, len(data), CHUNK):
        rpc(host, "FS.Put", {
            "filename": name,
            "data": base64.b64encode(data[i:i + CHUNK]).decode(),
            "append": i > 0,
        })
    if get_file(host, name) != data:
        raise SystemExit(f"Verification of {name} failed; device left unchanged.")


def swap_and_reboot(host: str, data: bytes, reboot: bool = True) -> None:
    put_file(host, "init_new.js", data)
    try:
        rpc(host, "FS.Remove", {"filename": "init.js"})
        rpc(host, "FS.Rename", {"src": "init_new.js", "dst": "init.js"})
    except (OSError, ValueError, urllib.error.URLError) as err:
        try:
            get_file(host, "init.js")
        except (OSError, ValueError, urllib.error.URLError):
            try:
                rpc(host, "FS.Rename", {"src": "init_new.js", "dst": "init.js"})
            except (OSError, ValueError, urllib.error.URLError) as recovery_err:
                raise SystemExit(
                    f"Patch replacement failed and recovery failed: {recovery_err}"
                ) from err
        raise SystemExit(f"Patch replacement failed: {err}") from err
    if get_file(host, "init.js") != data:
        raise SystemExit("init.js mismatch after rename. Re-run to retry.")
    if not reboot:
        return
    rpc(host, "Sys.Reboot", {"delay_ms": 500})
    print("Rebooting...")
    time.sleep(20)
    for _ in range(20):
        try:
            rpc(host, "Sys.GetInfo", timeout=3)
            return
        except (urllib.error.URLError, OSError):
            time.sleep(3)
    raise SystemExit("Device did not come back online.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("host")
    ap.add_argument("--restore", action="store_true")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="download and validate the current file without changing the device",
    )
    ap.add_argument(
        "--no-reboot",
        action="store_true",
        help="write the patch but do not reboot the controller",
    )
    args = ap.parse_args()

    info = rpc(args.host, "Sys.GetInfo")
    if info.get("app") != "aqualoop-controller":
        raise SystemExit(f"Not an Aqualoop controller: {info.get('app')}")
    dev = re.sub(r"[^0-9A-Za-z_-]", "_", str(info.get("mac", "device")))
    backup = HERE / f"init.js.{dev}.orig"
    current = get_file(args.host, "init.js")

    if args.restore:
        if not backup.exists():
            raise SystemExit(f"No backup found at {backup}")
        if args.dry_run:
            print(f"Restore backup available: {backup}")
            return
        swap_and_reboot(args.host, backup.read_bytes(), reboot=not args.no_reboot)
        print("Original init.js restored.")
        return

    try:
        text = current.decode("utf-8")
    except UnicodeDecodeError as err:
        raise SystemExit("init.js is not valid UTF-8; refusing to modify it.") from err
    if MARKER in text:
        original = text[: text.index(MARKER)].rstrip()
        if not backup.exists():
            backup.write_bytes(original.encode("utf-8"))
            print(f"Backup recovered from existing patch: {backup}")
    else:
        original = text.rstrip()
        if not backup.exists():
            backup.write_bytes(current)
            print(f"Backup saved: {backup}")
    patched = (original + "\n\n" + PATCH.replace("\r\n", "\n")).encode("utf-8")
    if args.dry_run:
        print("Patch required." if patched != current else "Patch already installed.")
        return
    if patched == current:
        print("Patch already installed.")
    else:
        swap_and_reboot(args.host, patched, reboot=not args.no_reboot)

    if args.no_reboot:
        return
    time.sleep(10)
    try:
        print("Heater.Get:", json.dumps(rpc(args.host, "Heater.Get")))
    except urllib.error.HTTPError as err:
        raise SystemExit(f"Patch installed but Heater.Get failed ({err.code}).")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as err:
        sys.exit(f"Cannot reach device: {err}")
