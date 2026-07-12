"""Entity descriptions for Tandem binary sensors.

`TANDEM_BINARY_SENSORS` is an empty tuple — the Tandem Source API exposes no
generic binary-sensor-shaped fields (null-not-guess). `DATA_STALE` is the
dedicated health-surface description used by TandemDataStaleBinarySensor (see
binary_sensor.py), which is wired unconditionally rather than from this tuple.
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory

TANDEM_BINARY_SENSORS: tuple[BinarySensorEntityDescription, ...] = ()

# STANDARD-stable-anchor-reconciliation rule 3 (relayed): the silent no-op
# (stale decision inputs going unavailable) must become an operator-visible
# amber. This is that named health surface.
DATA_STALE = BinarySensorEntityDescription(
    key="data_stale",
    name="Data stale",
    device_class=BinarySensorDeviceClass.PROBLEM,
    entity_category=EntityCategory.DIAGNOSTIC,
    icon="mdi:cloud-alert",
)
