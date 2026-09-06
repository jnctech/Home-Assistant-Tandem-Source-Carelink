"""Diagnostics support for the Tandem integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import TO_REDACT
from .coordinator import TandemConfigEntry
from .util import sanitize_for_logging


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: TandemConfigEntry) -> dict[str, Any]:
    """Return redacted diagnostics for a config entry.

    Credentials/PII in the entry are removed via async_redact_data(TO_REDACT);
    coordinator data is additionally run through sanitize_for_logging so any
    nested pump-report PII (names, serials) is redacted before export.
    """
    coordinator = entry.runtime_data.coordinator
    return {
        "entry": {
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": async_redact_data(entry.options, TO_REDACT),
        },
        "coordinator_data": sanitize_for_logging(coordinator.data or {}),
    }
