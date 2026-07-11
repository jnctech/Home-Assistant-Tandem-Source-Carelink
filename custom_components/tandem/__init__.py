"""Tandem t:slim integration for Home Assistant.

Thin setup shell: builds the Source API client, wires the coordinator, forwards
the sensor/binary_sensor platforms, and registers the import_history /
capture_diagnostics services. All parsing/compute lives in coordinator.py.
"""

from __future__ import annotations

import functools
import json
import logging
from datetime import date, datetime, timedelta, timezone

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.httpx_client import get_async_client

from .const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_REGION,
    COORDINATOR,
    DOMAIN,
    PLATFORMS,
    SCAN_INTERVAL,
    TANDEM_CLIENT,
)
from .coordinator import TandemCoordinator
from .tandem_api import TandemSourceClient
from .util import convert_date_to_isodate, sanitize_for_logging

__all__ = [
    "TandemCoordinator",
    "TandemSourceClient",
    "async_setup_entry",
    "async_unload_entry",
    "convert_date_to_isodate",
    "sanitize_for_logging",
]

_LOGGER = logging.getLogger(__name__)

SERVICE_IMPORT_HISTORY = "import_history"
SERVICE_CAPTURE_DIAGNOSTICS = "capture_diagnostics"


def _register_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register the Tandem service actions (idempotent)."""
    if not hass.services.has_service(DOMAIN, SERVICE_IMPORT_HISTORY):
        hass.services.async_register(
            DOMAIN,
            SERVICE_IMPORT_HISTORY,
            functools.partial(_handle_import_history, hass, entry.entry_id),
        )
    if not hass.services.has_service(DOMAIN, SERVICE_CAPTURE_DIAGNOSTICS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_CAPTURE_DIAGNOSTICS,
            functools.partial(_handle_capture_diagnostics, hass, entry.entry_id),
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tandem from a config entry."""
    config = entry.data

    try:
        client = TandemSourceClient(
            email=config[CONF_EMAIL],
            password=config[CONF_PASSWORD],
            region=config.get(CONF_REGION, "EU"),
            session=get_async_client(hass),
        )
    except Exception as err:
        raise ConfigEntryNotReady(f"Failed to initialise Tandem client: {err}") from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {TANDEM_CLIENT: client}

    coordinator = TandemCoordinator(hass, entry, update_interval=timedelta(seconds=config[SCAN_INTERVAL]))
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id][COORDINATOR] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _register_services(hass, entry)

    _LOGGER.info("Tandem entry setup completed: %s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        for service in (SERVICE_IMPORT_HISTORY, SERVICE_CAPTURE_DIAGNOSTICS):
            if hass.services.has_service(DOMAIN, service):
                hass.services.async_remove(DOMAIN, service)
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        client = entry_data.get(TANDEM_CLIENT)
        if client is not None:
            try:
                await client.close()
            except Exception as error:  # noqa: BLE001 - close must not raise during unload
                _LOGGER.warning("Failed to close Tandem client: %s", error)
    return unload_ok


async def _handle_import_history(hass: HomeAssistant, entry_id: str, call: ServiceCall) -> None:
    """Handle the tandem.import_history service call.

    Fetches pump events for the requested date range in 7-day chunks and imports
    them as long-term statistics (CGM glucose, active insulin, basal rate).
    """
    coordinator = hass.data[DOMAIN][entry_id][COORDINATOR]

    start_str: str = call.data["start_date"]
    end_str: str = call.data.get("end_date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    _LOGGER.info("[Tandem] import_history: importing events %s → %s", start_str, end_str)

    try:
        await coordinator.client.login()
    except Exception as err:
        _LOGGER.error("[Tandem] import_history: authentication failed: %s", err)
        return

    # Retrieve tconnectDeviceId from pump metadata
    try:
        metadata_list = await coordinator.client.get_pump_event_metadata()
        metadata_entry = None
        if isinstance(metadata_list, list) and metadata_list:
            metadata_entry = metadata_list[0]
        elif isinstance(metadata_list, dict):
            metadata_entry = metadata_list
        device_id = metadata_entry.get("tconnectDeviceId") if metadata_entry else None
    except Exception as err:
        _LOGGER.error("[Tandem] import_history: metadata fetch failed: %s", err)
        return

    if not device_id:
        _LOGGER.error("[Tandem] import_history: no tconnectDeviceId found in pump metadata")
        return

    # Fetch events in 7-day chunks to avoid API timeouts on large date ranges
    chunk_start = date.fromisoformat(start_str)
    chunk_end_limit = date.fromisoformat(end_str)
    all_events: list[dict] = []

    while chunk_start <= chunk_end_limit:
        chunk_end = min(chunk_start + timedelta(days=6), chunk_end_limit)
        try:
            events = await coordinator.client.get_pump_events(
                device_id,
                chunk_start.isoformat(),
                chunk_end.isoformat(),
            )
            if events:
                all_events.extend(events)
        except Exception as err:
            _LOGGER.warning(
                "[Tandem] import_history: chunk %s → %s failed: %s",
                chunk_start.isoformat(),
                chunk_end.isoformat(),
                err,
            )
        chunk_start = chunk_end + timedelta(days=1)

    _LOGGER.info("[Tandem] import_history: fetched %d events total", len(all_events))

    if all_events:
        await coordinator._import_statistics(all_events)
    else:
        _LOGGER.warning(
            "[Tandem] import_history: no events returned for %s → %s",
            start_str,
            end_str,
        )


async def _handle_capture_diagnostics(hass: HomeAssistant, entry_id: str, call: ServiceCall) -> None:
    """Handle the tandem.capture_diagnostics service call.

    Fetches raw API responses and writes a sanitised diagnostic snapshot to
    /config/tandem_diagnostics_<timestamp>.json for schema documentation
    and troubleshooting.
    """
    coordinator = hass.data[DOMAIN][entry_id][COORDINATOR]

    try:
        await coordinator.client.login()
    except Exception as err:
        _LOGGER.error("[Tandem] capture_diagnostics: authentication failed: %s", err)
        return

    snapshot: dict = {"captured_at": datetime.now(timezone.utc).isoformat()}

    # 1. Raw pump metadata (contains schema fields we need to document)
    try:
        metadata_list = await coordinator.client.get_pump_event_metadata()
        snapshot["pump_event_metadata"] = sanitize_for_logging(metadata_list)
    except Exception as err:
        snapshot["pump_event_metadata_error"] = str(err)

    # 2. Pumper info
    try:
        pumper_info = await coordinator.client.get_pumper_info()
        snapshot["pumper_info"] = sanitize_for_logging(pumper_info)
    except Exception as err:
        snapshot["pumper_info_error"] = str(err)

    # 3. Pump events — decode and summarise (full events too large)
    device_id = None
    if snapshot.get("pump_event_metadata"):
        meta = snapshot["pump_event_metadata"]
        if isinstance(meta, list) and meta:
            device_id = meta[0].get("tconnectDeviceId")
        elif isinstance(meta, dict):
            device_id = meta.get("tconnectDeviceId")

    if device_id:
        from zoneinfo import ZoneInfo

        tz_name = coordinator.timezone or "UTC"
        try:
            tz = ZoneInfo(tz_name)
        except (KeyError, TypeError):
            tz = ZoneInfo("UTC")

        now_pump = datetime.now(tz)
        start = (now_pump - timedelta(days=7)).strftime("%Y-%m-%d")
        end = now_pump.strftime("%Y-%m-%d")

        try:
            events = await coordinator.client.get_pump_events(device_id, start, end)
            if events:
                # Event ID distribution
                id_counts: dict[str, int] = {}
                for evt in events:
                    name = evt.get("event_name", f"Event_{evt.get('event_id')}")
                    id_counts[name] = id_counts.get(name, 0) + 1
                snapshot["pump_events_summary"] = {
                    "date_range": f"{start} to {end}",
                    "total_events": len(events),
                    "event_counts": dict(sorted(id_counts.items())),
                }
                # Include sample of each event type (first occurrence)
                seen_types: set[str] = set()
                samples: list[dict] = []
                for evt in events:
                    name = evt.get("event_name", "unknown")
                    if name not in seen_types:
                        seen_types.add(name)
                        sample = dict(evt)
                        # Convert datetime to string for JSON
                        if "timestamp" in sample:
                            sample["timestamp"] = str(sample["timestamp"])
                        samples.append(sample)
                snapshot["pump_events_samples"] = samples
            else:
                snapshot["pump_events_summary"] = {"total_events": 0}
        except Exception as err:
            snapshot["pump_events_error"] = str(err)

    # 4. Current sensor state (keys and their types/values)
    if coordinator.data:
        sensor_state: dict = {}
        for k, v in coordinator.data.items():
            if v is None:
                sensor_state[k] = "UNAVAILABLE"
            elif hasattr(v, "isoformat"):
                sensor_state[k] = v.isoformat()
            else:
                sensor_state[k] = v
        snapshot["current_sensor_state"] = sanitize_for_logging(sensor_state)

    # Write to HA config directory
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = hass.config.path(f"tandem_diagnostics_{ts_str}.json")

    try:
        import aiofiles

        async with aiofiles.open(out_path, "w") as f:
            await f.write(json.dumps(snapshot, indent=2, default=str))
        _LOGGER.info("[Tandem] Diagnostic snapshot written to %s", out_path)
    except ImportError:
        # aiofiles not available — fall back to sync write in executor
        import asyncio

        def _write():
            with open(out_path, "w") as f:
                json.dump(snapshot, f, indent=2, default=str)

        await asyncio.get_running_loop().run_in_executor(None, _write)
        _LOGGER.info("[Tandem] Diagnostic snapshot written to %s", out_path)
