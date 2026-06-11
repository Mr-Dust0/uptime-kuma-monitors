#!/usr/bin/env python3
"""Provision Uptime Kuma monitors from a YAML file.

Idempotent: monitors are matched by `name`. An existing monitor is updated in
place; a new name creates a new monitor. Nothing is ever deleted.

Configured entirely through environment variables:
    KUMA_URL       e.g. http://uptime-kuma:3001
    KUMA_USERNAME  admin account username (created on first run)
    KUMA_PASSWORD  admin account password
    MONITORS_FILE  path to the YAML file (default: /app/monitors.yaml)
"""
import os
import sys
import time

import yaml
from uptime_kuma_api import UptimeKumaApi, MonitorType, UptimeKumaException

KUMA_URL = os.environ.get("KUMA_URL", "http://uptime-kuma:3001")
USERNAME = os.environ.get("KUMA_USERNAME", "admin")
PASSWORD = os.environ.get("KUMA_PASSWORD")
MONITORS_FILE = os.environ.get("MONITORS_FILE", "/app/monitors.yaml")

# Map the friendly `type:` strings in monitors.yaml to the API enum.
TYPE_MAP = {
    "http": MonitorType.HTTP,
    "https": MonitorType.HTTP,
    "port": MonitorType.PORT,
    "tcp": MonitorType.PORT,
    "ping": MonitorType.PING,
    "dns": MonitorType.DNS,
    "docker": MonitorType.DOCKER,
    "keyword": MonitorType.KEYWORD,
}


def log(msg):
    print(f"[provisioner] {msg}", flush=True)


def connect_with_retry(retries=30, delay=2):
    """Wait for Kuma to come up, then connect."""
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            api = UptimeKumaApi(KUMA_URL)
            log(f"connected to {KUMA_URL}")
            return api
        except Exception as e:  # noqa: BLE001 - socket.io errors vary
            last_err = e
            log(f"waiting for Kuma ({attempt}/{retries})...")
            time.sleep(delay)
    raise SystemExit(f"could not reach Kuma at {KUMA_URL}: {last_err}")


def authenticate(api):
    """Create the admin account on first run, otherwise log in."""
    if api.need_setup():
        log("first run - creating admin account")
        api.setup(USERNAME, PASSWORD)
    api.login(USERNAME, PASSWORD)
    log(f"authenticated as {USERNAME}")


def normalise(entry):
    """Turn a YAML entry into kwargs for add_monitor/edit_monitor."""
    entry = dict(entry)
    name = entry.pop("name")
    raw_type = str(entry.pop("type", "http")).lower()
    if raw_type not in TYPE_MAP:
        raise ValueError(
            f"monitor '{name}': unknown type '{raw_type}'. "
            f"Known types: {', '.join(sorted(TYPE_MAP))}"
        )
    kwargs = {"name": name, "type": TYPE_MAP[raw_type]}
    kwargs.update(entry)  # url, hostname, port, interval, and any extra fields
    return name, kwargs


def main():
    if not PASSWORD:
        raise SystemExit("KUMA_PASSWORD is required")

    with open(MONITORS_FILE) as f:
        wanted = yaml.safe_load(f) or []
    if not isinstance(wanted, list):
        raise SystemExit(f"{MONITORS_FILE} must be a YAML list of monitors")

    api = connect_with_retry()
    try:
        authenticate(api)

        existing = {m["name"]: m for m in api.get_monitors()}
        created = updated = 0

        for entry in wanted:
            name, kwargs = normalise(entry)
            try:
                if name in existing:
                    api.edit_monitor(existing[name]["id"], **kwargs)
                    log(f"updated  : {name}")
                    updated += 1
                else:
                    api.add_monitor(**kwargs)
                    log(f"created  : {name}")
                    created += 1
            except UptimeKumaException as e:
                log(f"FAILED   : {name} -> {e}")

        log(f"done. {created} created, {updated} updated, "
            f"{len(wanted)} total in file.")
    finally:
        api.disconnect()


if __name__ == "__main__":
    sys.exit(main())
