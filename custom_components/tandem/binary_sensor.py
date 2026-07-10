"""Tandem binary sensor platform.

Currently a declared seam with no descriptions — the Tandem Source API exposes
no binary-sensor-shaped fields (null-not-guess). Kept so future additions have a
home without changing __init__ platform wiring.
"""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .binary_sensor_types import TANDEM_BINARY_SENSORS
from .const import COORDINATOR, DOMAIN
from .entity import PARALLEL_UPDATES, TandemEntity  # noqa: F401  (PARALLEL_UPDATES re-exported for HA)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tandem binary sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    entities = [TandemBinarySensor(coordinator, desc) for desc in TANDEM_BINARY_SENSORS]
    async_add_entities(entities)
    _LOGGER.debug("Binary sensor setup: %d entities", len(entities))


class TandemBinarySensor(TandemEntity, BinarySensorEntity):
    """A Tandem binary sensor backed by a coordinator data key."""

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
