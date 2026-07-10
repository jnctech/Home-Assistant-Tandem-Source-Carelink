"""Helper utilities for the Tandem integration (staleness + device identity)."""

from __future__ import annotations

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt as dt_util

from .const import (
    DEVICE_PUMP_MANUFACTURER,
    DEVICE_PUMP_MODEL,
    DEVICE_PUMP_SERIAL,
    DOMAIN,
    TANDEM_DATA_STALE_TIMEDELTA,
    TANDEM_SENSOR_KEY_LASTSG_TIMESTAMP,
    TANDEM_SENSOR_KEY_SOFTWARE_VERSION,
)


def is_data_stale(coordinator_data: dict | None) -> bool:
    """Check whether Tandem pump data is stale.

    Compares the last CGM reading timestamp against current UTC time. Returns
    True if data is older than ``TANDEM_DATA_STALE_TIMEDELTA``. All
    non-always-available Tandem sensors go stale together because they all
    originate from the same pump upload.
    """
    if not coordinator_data:
        return True

    last_sg_time = coordinator_data.get(TANDEM_SENSOR_KEY_LASTSG_TIMESTAMP)
    if last_sg_time is None or last_sg_time == STATE_UNAVAILABLE:
        return True

    now = dt_util.utcnow()

    if last_sg_time.tzinfo is None:
        last_sg_time = last_sg_time.replace(tzinfo=now.tzinfo)

    return (now - last_sg_time) >= TANDEM_DATA_STALE_TIMEDELTA


def pump_device_info(coordinator) -> DeviceInfo:
    """Build a DeviceInfo for the pump coordinator (single source of truth)."""
    data = coordinator.data or {}
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.entry_id)},
        name="Tandem",
        manufacturer=data.get(DEVICE_PUMP_MANUFACTURER, "Tandem Diabetes Care"),
        model=data.get(DEVICE_PUMP_MODEL),
        sw_version=data.get(TANDEM_SENSOR_KEY_SOFTWARE_VERSION),
        serial_number=data.get(DEVICE_PUMP_SERIAL),
        configuration_url=coordinator.configuration_url,
    )
