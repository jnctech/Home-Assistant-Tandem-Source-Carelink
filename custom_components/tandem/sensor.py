"""Tandem sensor platform."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import COORDINATOR, DOMAIN
from .entity import PARALLEL_UPDATES, TandemEntity  # noqa: F401  (PARALLEL_UPDATES re-exported for HA)
from .sensor_types import TANDEM_SENSORS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tandem sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    entities = [TandemSensor(coordinator, desc) for desc in TANDEM_SENSORS]
    async_add_entities(entities)
    _LOGGER.debug("Sensor setup: %d entities", len(entities))


class TandemSensor(TandemEntity, SensorEntity):
    """A Tandem sensor backed by a coordinator data key."""

    @property
    def native_value(self):
        """Return the value for this sensor's data key, or None if absent."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.sensor_description.key)

    @property
    def device_class(self) -> SensorDeviceClass | None:
        """Return the sensor device class."""
        return self.sensor_description.device_class

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        return self.sensor_description.native_unit_of_measurement

    @property
    def state_class(self) -> SensorStateClass | None:
        """Return the state class."""
        return self.sensor_description.state_class

    @property
    def extra_state_attributes(self):
        """Return the per-sensor attributes stored under ``<key>_attributes``."""
        if self.coordinator.data is None:
            return {}
        return self.coordinator.data.get(f"{self.sensor_description.key}_attributes", {})
