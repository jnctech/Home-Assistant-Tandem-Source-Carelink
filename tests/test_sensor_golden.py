"""Entity-golden (snapshot) tests for the Tandem platforms.

Layer L1 per the entity-golden framework (ported from mikrotik ADR-014): set the
integration up through the REAL setup path (MockConfigEntry + async_setup with the
Source client mocked at the boundary), then snapshot every produced entity's
state + attributes + registry entry with syrupy.

Determinism is mandatory (ADR-014 rule 2): a FIXED entry_id (so unique_ids don't
churn) and a FROZEN clock just after the fixture's CGM reading (so decision-input
sensors read fresh, not stale). ``snapshot_platform`` requires one platform per
call, so each golden patches ``PLATFORMS`` to a single platform.

Each snapshot is PAIRED with load-bearing invariant asserts (STANDARD-code-quality
§1: a golden alone can be silently re-blessed wrong; the invariant encodes the
contract the bug would violate).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from freezegun import freeze_time
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry, snapshot_platform
from syrupy.assertion import SnapshotAssertion

from custom_components.tandem.const import DOMAIN

# Fixed so entity unique_ids (f"tandem_{entry_id}_{key}") are deterministic.
_ENTRY_ID = "01JTANDEMGOLDEN000000000000"
# The fixture CGM reading is /Date(1705320000000)/ = 2024-01-15 12:00:00 UTC.
# Freeze 5 min later so is_data_stale() reports fresh and decision-inputs render.
_FROZEN = "2024-01-15 12:05:00"


async def _setup(hass: HomeAssistant, recent_data: dict, platforms: list[Platform]) -> MockConfigEntry:
    """Set up the integration through the real path with a boundary-mocked client.

    ``platforms`` narrows the forwarded platforms so a per-platform golden sees
    only its own entities (snapshot_platform asserts a single platform).
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Tandem t:slim",
        entry_id=_ENTRY_ID,
        data={
            "platform_type": "tandem",
            "tandem_email": "test@example.com",
            "tandem_password": "testpassword",
            "tandem_region": "EU",
            "scan_interval": 300,
        },
    )
    entry.add_to_hass(hass)

    client = AsyncMock()
    client.login = AsyncMock(return_value=True)
    client.get_pump_event_metadata = AsyncMock(
        return_value=[{"maxDateWithEvents": "2024-01-15T12:00:00", "tconnectDeviceId": "dev-1"}]
    )
    client.get_recent_data = AsyncMock(return_value=recent_data)
    client.close = AsyncMock()

    with (
        patch("custom_components.tandem.TandemSourceClient", return_value=client),
        patch("custom_components.tandem.PLATFORMS", platforms),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_sensor_golden(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_tandem_recent_data: dict,
):
    """Snapshot every sensor entity, and assert load-bearing invariants."""
    with freeze_time(_FROZEN):
        entry = await _setup(hass, mock_tandem_recent_data, [Platform.SENSOR])

        await snapshot_platform(hass, entity_registry, snapshot, entry.entry_id)

        # ── Invariants (independent of the snapshot) ──────────────────────
        # 1. Identity anchored on the stable entry_id (stable-anchor rule 1).
        entities = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
        assert entities, "setup produced no sensor entities"
        for ent in entities:
            assert ent.unique_id.startswith(f"tandem_{_ENTRY_ID}_"), ent.unique_id

        # 2. Glucose is physiological and the two units agree exactly.
        mgdl = hass.states.get("sensor.tandem_last_glucose_level_mg_dl")
        mmol = hass.states.get("sensor.tandem_last_glucose_level_mmol")
        assert mgdl is not None and mmol is not None
        mgdl_v = float(mgdl.state)
        assert 20 < mgdl_v < 600, f"glucose {mgdl_v} mg/dL out of physiological range"
        assert float(mmol.state) == round(mgdl_v * 0.0555, 2), "mg/dL <-> mmol/L conversion drifted"

        # 3. Fresh decision-input is served (not swallowed to unavailable/unknown).
        assert mgdl.state not in ("unavailable", "unknown")


async def test_binary_sensor_golden(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_tandem_recent_data: dict,
):
    """Snapshot binary sensors; fresh data => the health surface reads not-stale."""
    with freeze_time(_FROZEN):
        entry = await _setup(hass, mock_tandem_recent_data, [Platform.BINARY_SENSOR])

        await snapshot_platform(hass, entity_registry, snapshot, entry.entry_id)

        stale = hass.states.get("binary_sensor.tandem_data_stale")
        assert stale is not None and stale.state == "off", "fresh data must not flag stale"


async def test_stale_data_marks_decision_inputs_unavailable(
    hass: HomeAssistant,
    mock_tandem_recent_data: dict,
):
    """With no time freeze, the 2024 fixture is stale => fail-visible (safety).

    Drives the fail-visible path end-to-end through real setup (both platforms):
    a regression that served stale glucose as live would fail here.
    """
    entry = await _setup(hass, mock_tandem_recent_data, [Platform.SENSOR, Platform.BINARY_SENSOR])
    assert entry.entry_id == _ENTRY_ID

    stale = hass.states.get("binary_sensor.tandem_data_stale")
    assert stale is not None and stale.state == "on", "old data must flag the stale health surface"

    mgdl = hass.states.get("sensor.tandem_last_glucose_level_mg_dl")
    assert mgdl is not None and mgdl.state == "unavailable", "stale glucose must be unavailable, not served as live"
