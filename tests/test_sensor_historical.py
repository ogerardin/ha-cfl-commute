"""Tests for historical sensor entities and summary sensor historical stats."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.cfl_commute.const import (
    ATTR_AVG_DELAY_7D,
    ATTR_AVG_DELAY_TODAY,
    ATTR_BEST_DAY,
    ATTR_DAILY_BREAKDOWN,
    ATTR_ON_TIME_PCT_7D,
    ATTR_ON_TIME_PCT_30D,
    ATTR_ON_TIME_PCT_TODAY,
    ATTR_REVERSE_AVG_DELAY_7D,
    ATTR_REVERSE_BEST_DAY,
    ATTR_REVERSE_ON_TIME_PCT_7D,
    ATTR_REVERSE_ON_TIME_PCT_30D,
    ATTR_REVERSE_ON_TIME_PCT_TODAY,
    ATTR_REVERSE_WORST_DAY,
    ATTR_TOTAL_OBSERVATIONS_TODAY,
    ATTR_WORST_DAY,
    DOMAIN,
)
from custom_components.cfl_commute.sensor import (
    CFLCommuteHistoricalDelaysSensor,
    CFLCommuteHistoricalReliabilitySensor,
    CFLCommuteSummarySensor,
)


def _make_stats_store(
    on_time_pct_today=97.19, on_time_pct_7d=98.1, on_time_pct_30d=98.1, avg_delay_7d=3.4
):
    """Return a mock stats store with preset values."""
    store = MagicMock()
    store.get_today_stats.return_value = {"on_time_pct": on_time_pct_today}
    store.get_rolling_stats.side_effect = lambda days: (
        {
            "on_time_pct": on_time_pct_7d,
            "avg_delay_minutes": avg_delay_7d,
            "days_with_data": 7,
        }
        if days == 7
        else {
            "on_time_pct": on_time_pct_30d,
            "avg_delay_minutes": avg_delay_7d,
            "days_with_data": 30,
        }
    )
    store.get_best_and_worst_days.return_value = {
        "best_day": {
            "date": "2026-05-18",
            "on_time_pct": 100.0,
            "avg_delay_minutes": 0.0,
        },
        "worst_day": {
            "date": "2026-05-17",
            "on_time_pct": 94.89,
            "avg_delay_minutes": 5.0,
        },
    }
    store.get_daily_breakdown.return_value = [
        {
            "date": "2026-05-17",
            "on_time_pct": 94.89,
            "avg_delay_minutes": 5.0,
            "total_observations": 10,
        },
        {
            "date": "2026-05-18",
            "on_time_pct": 100.0,
            "avg_delay_minutes": 0.0,
            "total_observations": 10,
        },
        {
            "date": "2026-05-19",
            "on_time_pct": 97.19,
            "avg_delay_minutes": 3.4,
            "total_observations": 10,
        },
    ]
    return store


def _make_summary_sensor(stats_store=None, hass_domain_data=None):
    """Return a (sensor, coordinator) pair with mocked dependencies."""
    coordinator = MagicMock()
    coordinator.origin_id = "200405060"
    coordinator.origin_name = "Luxembourg"
    coordinator.destination_id = "200426001"
    coordinator.destination_name = "Esch-sur-Alzette"
    coordinator.stats_store = stats_store
    coordinator.data = []

    commute_name = "Test Commute"

    sensor = CFLCommuteSummarySensor(
        coordinator=coordinator,
        commute_name=commute_name,
        origin={"id": "200405060", "name": "Luxembourg"},
        destination={"id": "200426001", "name": "Esch-sur-Alzette"},
        num_trains=3,
        minor_threshold=3,
        major_threshold=10,
        severe_threshold=15,
    )

    hass = MagicMock()
    hass.data = {DOMAIN: hass_domain_data if hass_domain_data is not None else {}}
    sensor.hass = hass

    return sensor, coordinator


class TestHistoricalReliabilitySensor:
    """Tests for CFLCommuteHistoricalReliabilitySensor."""

    def test_state_returns_7day_on_time_pct(self):
        """State is the 7-day rolling on-time percentage."""
        store = _make_stats_store(on_time_pct_7d=98.1)
        coordinator = MagicMock()
        coordinator.stats_store = store
        sensor = CFLCommuteHistoricalReliabilitySensor(coordinator, "Test")
        assert sensor.state == 98.1

    def test_state_none_when_no_store(self):
        """State is None when stats_store is not set."""
        coordinator = MagicMock()
        coordinator.stats_store = None
        sensor = CFLCommuteHistoricalReliabilitySensor(coordinator, "Test")
        assert sensor.state is None

    def test_attributes_includes_daily_breakdown(self):
        """extra_state_attributes includes daily_breakdown."""
        store = _make_stats_store()
        coordinator = MagicMock()
        coordinator.stats_store = store
        sensor = CFLCommuteHistoricalReliabilitySensor(coordinator, "Test")
        attrs = sensor.extra_state_attributes
        assert ATTR_ON_TIME_PCT_TODAY in attrs
        assert ATTR_ON_TIME_PCT_7D in attrs
        assert ATTR_ON_TIME_PCT_30D in attrs
        assert ATTR_DAILY_BREAKDOWN in attrs
        assert ATTR_TOTAL_OBSERVATIONS_TODAY in attrs

    def test_sensor_metadata(self):
        """Sensor has correct name, unique_id, icon, unit."""
        coordinator = MagicMock()
        coordinator.stats_store = None
        sensor = CFLCommuteHistoricalReliabilitySensor(coordinator, "Test Commute")
        assert sensor.name == "Test Commute Historical Reliability"
        assert sensor.unique_id == "Test Commute_historical_reliability"
        assert sensor.icon == "mdi:chart-line"
        assert sensor.unit_of_measurement == "%"


class TestHistoricalDelaysSensor:
    """Tests for CFLCommuteHistoricalDelaysSensor."""

    def test_state_returns_7day_avg_delay(self):
        """State is the 7-day rolling average delay in minutes."""
        store = _make_stats_store(avg_delay_7d=3.4)
        coordinator = MagicMock()
        coordinator.stats_store = store
        sensor = CFLCommuteHistoricalDelaysSensor(coordinator, "Test")
        assert sensor.state == 3.4

    def test_state_none_when_no_store(self):
        """State is None when stats_store is not set."""
        coordinator = MagicMock()
        coordinator.stats_store = None
        sensor = CFLCommuteHistoricalDelaysSensor(coordinator, "Test")
        assert sensor.state is None

    def test_attributes_include_best_worst(self):
        """extra_state_attributes includes avg_delay_today, best_day, worst_day."""
        store = _make_stats_store(avg_delay_7d=3.4)
        coordinator = MagicMock()
        coordinator.stats_store = store
        sensor = CFLCommuteHistoricalDelaysSensor(coordinator, "Test")
        attrs = sensor.extra_state_attributes
        assert ATTR_AVG_DELAY_TODAY in attrs
        assert ATTR_AVG_DELAY_7D in attrs
        assert ATTR_BEST_DAY in attrs
        assert ATTR_WORST_DAY in attrs

    def test_sensor_metadata(self):
        """Sensor has correct name, unique_id, icon, unit."""
        coordinator = MagicMock()
        coordinator.stats_store = None
        sensor = CFLCommuteHistoricalDelaysSensor(coordinator, "Test Commute")
        assert sensor.name == "Test Commute Historical Delays"
        assert sensor.unique_id == "Test Commute_historical_delays"
        assert sensor.icon == "mdi:clock-alert-outline"
        assert sensor.unit_of_measurement == "min"


class TestSummarySensorHistoricalStats:
    """Tests for historical stats on CommuteSummarySensor."""

    def test_summary_includes_historical_stats_when_store_present(self):
        """CommuteSummarySensor attrs include historical stats when stats_store is set."""
        store = _make_stats_store()
        sensor, _ = _make_summary_sensor(stats_store=store)

        attrs = sensor.extra_state_attributes

        assert ATTR_ON_TIME_PCT_TODAY in attrs
        assert ATTR_ON_TIME_PCT_7D in attrs
        assert ATTR_ON_TIME_PCT_30D in attrs
        assert ATTR_AVG_DELAY_7D in attrs
        assert ATTR_BEST_DAY in attrs
        assert ATTR_WORST_DAY in attrs
        assert ATTR_DAILY_BREAKDOWN not in attrs

    def test_summary_historical_stats_values_match_store(self):
        """CommuteSummarySensor historical stats match what the store returns."""
        store = _make_stats_store(
            on_time_pct_today=97.19,
            on_time_pct_7d=98.1,
            on_time_pct_30d=98.1,
            avg_delay_7d=3.4,
        )
        sensor, _ = _make_summary_sensor(stats_store=store)

        attrs = sensor.extra_state_attributes

        assert attrs[ATTR_ON_TIME_PCT_TODAY] == 97.19
        assert attrs[ATTR_ON_TIME_PCT_7D] == 98.1
        assert attrs[ATTR_ON_TIME_PCT_30D] == 98.1
        assert attrs[ATTR_AVG_DELAY_7D] == 3.4
        assert attrs[ATTR_BEST_DAY]["date"] == "2026-05-18"
        assert attrs[ATTR_WORST_DAY]["date"] == "2026-05-17"
        assert ATTR_DAILY_BREAKDOWN not in attrs

    def test_summary_no_historical_stats_when_store_absent(self):
        """CommuteSummarySensor attrs omit historical stats when stats_store is None."""
        sensor, _ = _make_summary_sensor(stats_store=None)

        attrs = sensor.extra_state_attributes

        assert ATTR_ON_TIME_PCT_TODAY not in attrs
        assert ATTR_ON_TIME_PCT_7D not in attrs
        assert ATTR_ON_TIME_PCT_30D not in attrs
        assert ATTR_AVG_DELAY_7D not in attrs
        assert ATTR_BEST_DAY not in attrs
        assert ATTR_WORST_DAY not in attrs
        assert ATTR_DAILY_BREAKDOWN not in attrs

    def test_summary_original_attrs_preserved(self):
        """Original summary attributes are preserved alongside new historical ones."""
        store = _make_stats_store()
        sensor, _ = _make_summary_sensor(stats_store=store)

        attrs = sensor.extra_state_attributes

        assert "on_time_count" in attrs
        assert "delayed_count" in attrs
        assert "cancelled_count" in attrs
        assert "total_trains" in attrs
        assert "all_trains" in attrs
        assert "origin" in attrs
        assert "destination" in attrs

    def test_reverse_stats_exposed_when_paired_coordinator_exists(self):
        """Reverse-route stats are exposed when a matching reverse coordinator exists."""
        fwd_store = _make_stats_store(on_time_pct_today=97.19, avg_delay_7d=3.4)
        rev_store = _make_stats_store(on_time_pct_today=85.0, avg_delay_7d=6.2)

        rev_coordinator = MagicMock()
        rev_coordinator.origin_id = "200426001"
        rev_coordinator.destination_id = "200405060"
        rev_coordinator.stats_store = rev_store

        sensor, _ = _make_summary_sensor(
            stats_store=fwd_store,
            hass_domain_data={"entry_rev": {"coordinator": rev_coordinator}},
        )

        attrs = sensor.extra_state_attributes

        assert ATTR_REVERSE_ON_TIME_PCT_TODAY in attrs
        assert ATTR_REVERSE_ON_TIME_PCT_7D in attrs
        assert ATTR_REVERSE_ON_TIME_PCT_30D in attrs
        assert ATTR_REVERSE_AVG_DELAY_7D in attrs
        assert ATTR_REVERSE_BEST_DAY in attrs
        assert ATTR_REVERSE_WORST_DAY in attrs

    def test_reverse_stats_values_match_paired_coordinator(self):
        """Reverse-route stats come from the paired coordinator's store."""
        fwd_store = _make_stats_store(on_time_pct_today=97.19, avg_delay_7d=3.4)
        rev_store = _make_stats_store(
            on_time_pct_today=85.0,
            on_time_pct_7d=87.5,
            on_time_pct_30d=88.0,
            avg_delay_7d=6.2,
        )

        rev_coordinator = MagicMock()
        rev_coordinator.origin_id = "200426001"
        rev_coordinator.destination_id = "200405060"
        rev_coordinator.stats_store = rev_store

        sensor, _ = _make_summary_sensor(
            stats_store=fwd_store,
            hass_domain_data={"entry_rev": {"coordinator": rev_coordinator}},
        )

        attrs = sensor.extra_state_attributes

        assert attrs[ATTR_ON_TIME_PCT_TODAY] == 97.19
        assert attrs[ATTR_AVG_DELAY_7D] == 3.4
        assert attrs[ATTR_REVERSE_ON_TIME_PCT_TODAY] == 85.0
        assert attrs[ATTR_REVERSE_ON_TIME_PCT_7D] == 87.5
        assert attrs[ATTR_REVERSE_ON_TIME_PCT_30D] == 88.0
        assert attrs[ATTR_REVERSE_AVG_DELAY_7D] == 6.2

    def test_reverse_stats_absent_when_no_paired_coordinator(self):
        """Reverse-route stats not included when no matching reverse coordinator."""
        fwd_store = _make_stats_store()
        sensor, _ = _make_summary_sensor(stats_store=fwd_store, hass_domain_data={})

        attrs = sensor.extra_state_attributes

        assert ATTR_REVERSE_ON_TIME_PCT_TODAY not in attrs
        assert ATTR_REVERSE_ON_TIME_PCT_7D not in attrs
        assert ATTR_REVERSE_AVG_DELAY_7D not in attrs

    def test_reverse_stats_absent_when_no_stats_store_on_reverse(self):
        """Reverse stats omitted when paired coordinator has no stats_store."""
        fwd_store = _make_stats_store()
        rev_coordinator = MagicMock()
        rev_coordinator.origin_id = "200426001"
        rev_coordinator.destination_id = "200405060"
        rev_coordinator.stats_store = None

        sensor, _ = _make_summary_sensor(
            stats_store=fwd_store,
            hass_domain_data={"entry_rev": {"coordinator": rev_coordinator}},
        )

        attrs = sensor.extra_state_attributes

        assert ATTR_REVERSE_ON_TIME_PCT_TODAY not in attrs
        assert ATTR_REVERSE_AVG_DELAY_7D not in attrs

    def test_coordinator_not_matched_as_own_reverse(self):
        """A coordinator is never matched as its own reverse."""
        fwd_store = _make_stats_store()
        sensor, own_coordinator = _make_summary_sensor(
            stats_store=fwd_store, hass_domain_data={}
        )

        own_coordinator.origin_id = "200426001"
        own_coordinator.destination_id = "200405060"
        sensor.hass.data[DOMAIN]["entry_self"] = {"coordinator": own_coordinator}

        attrs = sensor.extra_state_attributes

        assert ATTR_REVERSE_ON_TIME_PCT_TODAY not in attrs


class TestSummarySensorNonRegression:
    """Verify existing CFLCommuteSummarySensor behavior is unchanged."""

    def test_summary_sensor_state_format_unchanged(self):
        """State format returns same text as before."""
        coordinator = MagicMock()
        coordinator.data = []
        sensor = CFLCommuteSummarySensor(
            coordinator=coordinator,
            commute_name="Test",
            origin={"id": "1", "name": "Luxembourg"},
            destination={"id": "2", "name": "Esch"},
            num_trains=3,
            minor_threshold=3,
            major_threshold=10,
            severe_threshold=15,
        )
        assert sensor.state == "No trains"

    def test_summary_sensor_original_attrs_unchanged(self):
        """Original attribute keys are present and unchanged."""
        coordinator = MagicMock()
        coordinator.data = []
        coordinator.stats_store = None
        sensor = CFLCommuteSummarySensor(
            coordinator=coordinator,
            commute_name="Test",
            origin={"id": "1", "name": "Luxembourg"},
            destination={"id": "2", "name": "Esch"},
            num_trains=3,
            minor_threshold=3,
            major_threshold=10,
            severe_threshold=15,
        )
        attrs = sensor.extra_state_attributes
        assert attrs.get("origin") == "Luxembourg"
        assert attrs.get("destination") == "Esch"
        assert attrs.get("origin_id") == "1"
        assert attrs.get("destination_id") == "2"
