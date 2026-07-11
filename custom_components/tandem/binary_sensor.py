"""Tandem binary sensor platform.

Besides the (currently empty) declarative TANDEM_BINARY_SENSORS seam, this
platform always wires one health-surface entity: TandemDataStaleBinarySensor.
It reports whether the pump upload has gone stale — the named, operator-visible
"amber" that STANDARD-stable-anchor-reconciliation rule 3 (relayed) requires,
so a silently-unavailable glucose/insulin decision-input is never invisible.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .binary_sensor_types import DATA_STALE, TANDEM_BINARY_SENSORS
from .coordinator import TandemConfigEntry
from .entity import PARALLEL_UPDATES, TandemEntity  # noqa: F401  (PARALLEL_UPDATES re-exported for HA)
from .helpers import is_data_stale

if TYPE_CHECKING:
    from .coordinator import TandemCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TandemConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tandem binary sensor platform."""
    coordinator = entry.runtime_data.coordinator
    entities: list[BinarySensorEntity] = [TandemBinarySensor(coordinator, desc) for desc in TANDEM_BINARY_SENSORS]
    entities.append(TandemDataStaleBinarySensor(coordinator))
    async_add_entities(entities)
    _LOGGER.debug("Binary sensor setup: %d entities", len(entities))


class TandemBinarySensor(TandemEntity, BinarySensorEntity):
    """A Tandem binary sensor backed by a coordinator data key."""

    sensor_description: BinarySensorEntityDescription

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return the binary sensor device class."""
        return self.sensor_description.device_class

    @property
    def is_on(self) -> bool:
        """Return True when the backing data key is truthy."""
        if self.coordinator.data is None:
            return False
        return self.coordinator.data.get(self.sensor_description.key) is True


class TandemDataStaleBinarySensor(TandemEntity, BinarySensorEntity):
    """Health surface: on when the pump upload is stale.

    Always available so it can report staleness even once the data-bearing
    sensors have themselves gone unavailable (the base's fail-visible rule would
    otherwise hide this very indicator). device_class=problem so it renders as an
    operator-visible amber. See STANDARD-stable-anchor-reconciliation rule 3.
    """

    def __init__(self, coordinator: TandemCoordinator) -> None:
        """Bind the fixed DATA_STALE description."""
        super().__init__(coordinator, DATA_STALE)

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return the problem device class."""
        return BinarySensorDeviceClass.PROBLEM

    @property
    def available(self) -> bool:
        """Always report while the coordinator is healthy (health surfaces must not self-hide)."""
        return self.coordinator.last_update_success

    @property
    def is_on(self) -> bool:
        """Return True when the pump data is stale (decision inputs unavailable)."""
        return is_data_stale(self.coordinator.data)
