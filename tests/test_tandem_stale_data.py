"""Tests for stale data detection (Issue #11)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tandem.const import (
    DOMAIN,
    TANDEM_CLIENT,
    PLATFORM_TYPE,
    PLATFORM_TANDEM,
    TANDEM_DATA_STALE_TIMEDELTA,
    TANDEM_SENSOR_KEY_LASTSG_MMOL,
    TANDEM_SENSOR_KEY_LASTSG_TIMESTAMP,
    TANDEM_SENSOR_KEY_BASAL_RATE,
    TANDEM_SENSOR_KEY_ACTIVE_INSULIN,
    DEVICE_PUMP_SERIAL,
)
from custom_components.tandem.helpers import is_data_stale
from custom_components.tandem.sensor import TandemSensor
from custom_components.tandem.sensor_types import TANDEM_SENSORS_ALWAYS_AVAILABLE


# ═══════════════════════════════════════════════════════════════════════════
# Tests: is_data_stale helper
# ═══════════════════════════════════════════════════════════════════════════


class TestIsDataStale:
    """Tests for the is_data_stale() helper function."""

    def test_stale_when_data_is_empty(self):
        """Empty coordinator data should be considered stale."""
        assert is_data_stale({}) is True

    def test_stale_when_data_is_none(self):
        """None coordinator data should be considered stale."""
        assert is_data_stale(None) is True

    def test_stale_when_timestamp_missing(self):
        """Missing CGM timestamp should be considered stale."""
        data = {TANDEM_SENSOR_KEY_LASTSG_MMOL: 6.5}
        assert is_data_stale(data) is True

    def test_stale_when_timestamp_is_unavailable(self):
        """UNAVAILABLE CGM timestamp should be considered stale."""
        data = {TANDEM_SENSOR_KEY_LASTSG_TIMESTAMP: STATE_UNAVAILABLE}
        assert is_data_stale(data) is True

    @patch("custom_components.tandem.helpers.dt_util")
    def test_stale_when_old_timestamp(self, mock_dt_util):
        """Data older than threshold should be stale."""
        now = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
        mock_dt_util.utcnow.return_value = now

        # 7 hours ago — beyond 6-hour threshold
        old_time = now - timedelta(hours=7)
        data = {TANDEM_SENSOR_KEY_LASTSG_TIMESTAMP: old_time}
        assert is_data_stale(data) is True

    @patch("custom_components.tandem.helpers.dt_util")
    def test_fresh_when_recent_timestamp(self, mock_dt_util):
        """Data within threshold should not be stale."""
        now = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
        mock_dt_util.utcnow.return_value = now

        # 10 minutes ago — within 6-hour threshold
        recent_time = now - timedelta(minutes=10)
        data = {TANDEM_SENSOR_KEY_LASTSG_TIMESTAMP: recent_time}
        assert is_data_stale(data) is False

    @patch("custom_components.tandem.helpers.dt_util")
    def test_stale_at_exact_threshold(self, mock_dt_util):
        """Data exactly at the threshold should be stale (>= comparison)."""
        now = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
        mock_dt_util.utcnow.return_value = now

        boundary_time = now - TANDEM_DATA_STALE_TIMEDELTA
        data = {TANDEM_SENSOR_KEY_LASTSG_TIMESTAMP: boundary_time}
        assert is_data_stale(data) is True

    @patch("custom_components.tandem.helpers.dt_util")
    def test_fresh_just_before_threshold(self, mock_dt_util):
        """Data 1 second before threshold should not be stale."""
        now = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
        mock_dt_util.utcnow.return_value = now

        just_before = now - TANDEM_DATA_STALE_TIMEDELTA + timedelta(seconds=1)
        data = {TANDEM_SENSOR_KEY_LASTSG_TIMESTAMP: just_before}
        assert is_data_stale(data) is False

    @patch("custom_components.tandem.helpers.dt_util")
    def test_handles_naive_timestamp(self, mock_dt_util):
        """Naive (no timezone) timestamps should be handled gracefully."""
        now = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
        mock_dt_util.utcnow.return_value = now

        # Naive datetime, 10 minutes ago
        naive_time = datetime(2024, 1, 15, 13, 50, 0)
        data = {TANDEM_SENSOR_KEY_LASTSG_TIMESTAMP: naive_time}
        assert is_data_stale(data) is False


# ═══════════════════════════════════════════════════════════════════════════
# Tests: Sensor availability
# ═══════════════════════════════════════════════════════════════════════════


class TestSensorAvailability:
    """Tests for TandemEntity.available — fail-visible staleness (safety).

    Decision-input sensors (glucose, basal, IOB) go UNAVAILABLE when the pump
    upload is stale, so HA never serves a stale reading as if it were current
    (STANDARD-stable-anchor-reconciliation, relayed — a silently-dead
    decision-input entity is a safety event). Timestamp/diagnostic sensors stay
    available so the user can see WHEN data last arrived. This reverses the
    prior "diagnostic mode" that showed stale values as if live.
    """

    def _make_sensor(self, sensor_key: str, coordinator_data: dict | None = None) -> TandemSensor:
        """Create a TandemSensor with a mocked coordinator."""
        from homeassistant.components.sensor import SensorEntityDescription

        coordinator = MagicMock()
        coordinator.data = coordinator_data if coordinator_data is not None else {}
        # CoordinatorEntity.available checks coordinator.last_update_success
        coordinator.last_update_success = True

        description = SensorEntityDescription(key=sensor_key, name=f"Test {sensor_key}")
        return TandemSensor(coordinator, description)

    @staticmethod
    def _fresh() -> dict:
        """Coordinator data with a just-now CGM timestamp (not stale)."""
        return {TANDEM_SENSOR_KEY_LASTSG_TIMESTAMP: datetime.now(timezone.utc)}

    def test_glucose_unavailable_when_stale(self):
        """A stale glucose sensor must go unavailable, not show a stale value."""
        entity = self._make_sensor(TANDEM_SENSOR_KEY_LASTSG_MMOL)  # empty data -> stale
        assert entity.available is False

    def test_glucose_available_when_fresh(self):
        """Glucose sensor is available when the last reading is recent."""
        entity = self._make_sensor(TANDEM_SENSOR_KEY_LASTSG_MMOL, self._fresh())
        assert entity.available is True

    def test_basal_unavailable_when_stale(self):
        """A stale basal-rate sensor must go unavailable."""
        entity = self._make_sensor(TANDEM_SENSOR_KEY_BASAL_RATE)
        assert entity.available is False

    def test_iob_unavailable_when_stale(self):
        """A stale IOB sensor must go unavailable."""
        entity = self._make_sensor(TANDEM_SENSOR_KEY_ACTIVE_INSULIN)
        assert entity.available is False

    def test_decision_inputs_available_when_fresh(self):
        """Decision-input sensors are available when data is fresh."""
        for key in (TANDEM_SENSOR_KEY_BASAL_RATE, TANDEM_SENSOR_KEY_ACTIVE_INSULIN):
            entity = self._make_sensor(key, self._fresh())
            assert entity.available is True, f"{key} should be available when fresh"

    def test_always_available_sensors_stay_available_when_stale(self):
        """Timestamp/diagnostic sensors stay available even when data is stale."""
        for sensor_key in TANDEM_SENSORS_ALWAYS_AVAILABLE:
            entity = self._make_sensor(sensor_key)  # empty/stale data
            assert entity.available is True, f"Sensor {sensor_key} should remain available"

    def test_unavailable_when_coordinator_not_connected(self):
        """Sensor unavailable when the coordinator itself reports failure."""
        entity = self._make_sensor(TANDEM_SENSOR_KEY_LASTSG_MMOL, self._fresh())
        entity.coordinator.last_update_success = False
        assert entity.available is False


# ═══════════════════════════════════════════════════════════════════════════
# Tests: Coordinator maxDateWithEvents optimisation
# ═══════════════════════════════════════════════════════════════════════════


async def _setup_coordinator_for_stale_test(
    hass: HomeAssistant,
    metadata_side_effect: list | None = None,
    recent_data_side_effect: list | None = None,
    recent_data_return: dict | None = None,
) -> tuple:
    """Set up a TandemCoordinator with configurable metadata responses."""
    from custom_components.tandem import TandemCoordinator

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Tandem t:slim",
        data={
            "platform_type": "tandem",
            "tandem_email": "test@example.com",
            "tandem_password": "testpassword",
            "tandem_region": "EU",
            "scan_interval": 300,
        },
    )
    entry.add_to_hass(hass)
    entry.mock_state(hass, ConfigEntryState.SETUP_IN_PROGRESS)

    mock_client = AsyncMock()
    mock_client.login = AsyncMock(return_value=True)
    mock_client.close = AsyncMock()

    if metadata_side_effect:
        mock_client.get_pump_event_metadata = AsyncMock(side_effect=metadata_side_effect)
    else:
        mock_client.get_pump_event_metadata = AsyncMock(return_value=[{"maxDateWithEvents": "2024-01-15T12:00:00"}])

    if recent_data_side_effect:
        mock_client.get_recent_data = AsyncMock(side_effect=recent_data_side_effect)
    elif recent_data_return:
        mock_client.get_recent_data = AsyncMock(return_value=recent_data_return)
    else:
        mock_client.get_recent_data = AsyncMock(return_value=_default_recent_data())

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        TANDEM_CLIENT: mock_client,
        PLATFORM_TYPE: PLATFORM_TANDEM,
    }

    coordinator = TandemCoordinator(hass, entry, update_interval=timedelta(seconds=300))

    return coordinator, mock_client


def _default_recent_data() -> dict[str, Any]:
    """Return default mock recent data for tests."""
    return {
        "pump_metadata": {
            "serialNumber": "12345678",
            "modelNumber": "t:slim X2",
            "softwareVersion": "7.6.0",
            "lastUpload": "/Date(1705320000000)/",
            "maxDateWithEvents": "2024-01-15T12:00:00",
        },
        "pumper_info": {
            "firstName": "Test",
            "lastName": "User",
        },
        "pump_events": None,
        "therapy_timeline": {
            "cgm": [
                {
                    "EventDateTime": "/Date(1705320000000)/",
                    "Readings": [{"Value": 120, "Type": "EGV"}],
                }
            ],
            "bolus": [],
            "basal": [],
        },
        "dashboard_summary": None,
    }


class TestCoordinatorMaxDateOptimisation:
    """Tests for skipping pumpevents when maxDateWithEvents is unchanged."""

    async def test_first_poll_always_fetches(self, hass: HomeAssistant):
        """First poll should always fetch pump events (no cached maxDate)."""
        coordinator, mock_client = await _setup_coordinator_for_stale_test(hass)

        await coordinator.async_config_entry_first_refresh()

        # get_recent_data should have been called (first poll, no cache)
        mock_client.get_recent_data.assert_called_once()
        assert coordinator._last_max_date == "2024-01-15T12:00:00"

    async def test_skips_fetch_when_max_date_unchanged(self, hass: HomeAssistant):
        """Second poll with same maxDateWithEvents should skip pumpevents."""
        coordinator, mock_client = await _setup_coordinator_for_stale_test(
            hass,
            metadata_side_effect=[
                [{"maxDateWithEvents": "2024-01-15T12:00:00"}],
                [{"maxDateWithEvents": "2024-01-15T12:00:00"}],  # Same
            ],
        )

        await coordinator.async_config_entry_first_refresh()
        assert mock_client.get_recent_data.call_count == 1

        # Second refresh — same maxDate, should skip
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # get_recent_data should NOT have been called again
        assert mock_client.get_recent_data.call_count == 1

    async def test_fetches_when_max_date_changes(self, hass: HomeAssistant):
        """Poll should fetch when maxDateWithEvents changes."""
        second_data = _default_recent_data()
        second_data["pump_metadata"]["maxDateWithEvents"] = "2024-01-15T12:30:00"

        coordinator, mock_client = await _setup_coordinator_for_stale_test(
            hass,
            metadata_side_effect=[
                [{"maxDateWithEvents": "2024-01-15T12:00:00"}],
                [{"maxDateWithEvents": "2024-01-15T12:30:00"}],  # Changed!
            ],
            recent_data_side_effect=[
                _default_recent_data(),
                second_data,
            ],
        )

        await coordinator.async_config_entry_first_refresh()
        assert mock_client.get_recent_data.call_count == 1

        # Second refresh — different maxDate, should fetch
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        assert mock_client.get_recent_data.call_count == 2
        assert coordinator._last_max_date == "2024-01-15T12:30:00"

    async def test_cached_data_preserved_on_skip(self, hass: HomeAssistant):
        """When skipping fetch, sensor data from previous poll should be preserved."""
        coordinator, mock_client = await _setup_coordinator_for_stale_test(
            hass,
            metadata_side_effect=[
                [{"maxDateWithEvents": "2024-01-15T12:00:00"}],
                [{"maxDateWithEvents": "2024-01-15T12:00:00"}],  # Same
            ],
        )

        await coordinator.async_config_entry_first_refresh()
        first_data = dict(coordinator.data)

        # Second refresh — should skip but preserve data
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        assert coordinator.data[DEVICE_PUMP_SERIAL] == first_data[DEVICE_PUMP_SERIAL]

    async def test_metadata_failure_falls_through_to_full_fetch(self, hass: HomeAssistant):
        """If metadata check fails, should proceed with full fetch."""
        coordinator, mock_client = await _setup_coordinator_for_stale_test(
            hass,
            metadata_side_effect=[
                Exception("API timeout"),  # Metadata fails
            ],
        )

        await coordinator.async_config_entry_first_refresh()

        # Should still have called get_recent_data despite metadata failure
        mock_client.get_recent_data.assert_called_once()
