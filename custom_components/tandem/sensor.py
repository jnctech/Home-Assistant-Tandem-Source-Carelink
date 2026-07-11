"""Tandem sensor platform."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, cast

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import TandemConfigEntry
from .entity import PARALLEL_UPDATES, TandemEntity  # noqa: F401  (PARALLEL_UPDATES re-exported for HA)
from .sensor_types import TANDEM_SENSORS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TandemConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tandem sensor platform."""
    coordinator = entry.runtime_data.coordinator
    entities = [TandemSensor(coordinator, desc) for desc in TANDEM_SENSORS]
    async_add_entities(entities)
    _LOGGER.debug("Sensor setup: %d entities", len(entities))


class TandemSensor(TandemEntity, SensorEntity):
    """A Tandem sensor backed by a coordinator data key."""

    sensor_description: SensorEntityDescription

    @property
    def native_value(self) -> StateType | datetime:
        """Return the value for this sensor's data key, or None if absent."""
        data = self.coordinator.data
        if data is None:
            return None
        return cast("StateType | datetime", data.get(self.sensor_description.key))

    @property
    def device_class(self) -> SensorDeviceClass | None:
        """Return the sensor device class."""
        return self.sensor_description.device_class

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        return self.sensor_description.native_unit_of_measurement

    @property
    def state_class(self) -> SensorStateClass | str | None:
        """Return the state class."""
        return self.sensor_description.state_class

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the per-sensor attributes stored under ``<key>_attributes``."""
        data = self.coordinator.data
        if data is None:
            return {}
        return cast("dict[str, Any]", data.get(f"{self.sensor_description.key}_attributes", {}))
