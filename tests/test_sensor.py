"""Tests for sensor logic."""

import json
from unittest.mock import MagicMock

from custom_components.cfl_commute.api import Departure
from custom_components.cfl_commute.const import (
    STATUS_NORMAL,
    STATUS_MINOR,
    STATUS_MAJOR,
    STATUS_SEVERE,
    STATUS_CRITICAL,
)
from custom_components.cfl_commute.sensor import (
    CFLCommuteSummarySensor,
    CFLCommuteNextTrainSensor,
    CFLCommuteTrainSensor,
)


def _make_coordinator(departures: list[Departure]):
    """Create a mock coordinator with the given departures as data."""
    coordinator = MagicMock()
    coordinator.data = departures
    return coordinator


def _make_origin_destination():
    """Return default origin/destination dicts."""
    return {"id": "200405060", "name": "Luxembourg"}, {
        "id": "200417025",
        "name": "Esch-sur-Alzette",
    }


def _make_departure(
    train_number: str = "RE 4632",
    scheduled_departure: str = "08:00:00",
    expected_departure: str = "08:00:00",
    platform: str = "3",
    direction: str = "Esch-sur-Alzette",
    operator: str = "CFL",
    delay_minutes: int = 0,
    is_cancelled: bool = False,
    calling_points: list | None = None,
) -> Departure:
    """Create a test Departure with sensible defaults."""
    return Departure(
        station_id="200405060",
        scheduled_departure=scheduled_departure,
        expected_departure=expected_departure,
        platform=platform,
        line="RE",
        direction=direction,
        operator=operator,
        train_number=train_number,
        is_cancelled=is_cancelled,
        delay_minutes=delay_minutes,
        calling_points=calling_points or ["Bettembourg", "Esch-sur-Alzette"],
        stop_ids=["200417025", "200417025"],
        journey_ref="",
    )


def calculate_status(departures, minor_threshold, major_threshold, severe_threshold):
    """Extract status calculation logic for testing."""
    if not departures:
        return STATUS_NORMAL

    if any(d.get("is_cancelled") for d in departures):
        return STATUS_CRITICAL

    max_delay = max((d.get("delay_minutes", 0) for d in departures), default=0)

    if max_delay >= severe_threshold:
        return STATUS_SEVERE
    elif max_delay >= major_threshold:
        return STATUS_MAJOR
    elif max_delay >= minor_threshold:
        return STATUS_MINOR

    return STATUS_NORMAL


def calculate_summary(departures, minor_threshold):
    """Extract summary calculation logic for testing."""
    if not departures:
        return "No trains"

    on_time = sum(
        1
        for d in departures
        if not d.get("is_cancelled") and d.get("delay_minutes", 0) < minor_threshold
    )
    delayed = sum(
        1
        for d in departures
        if not d.get("is_cancelled") and d.get("delay_minutes", 0) >= minor_threshold
    )
    cancelled = sum(1 for d in departures if d.get("is_cancelled"))

    parts = []
    if on_time:
        parts.append(f"{on_time} on time")
    if delayed:
        parts.append(f"{delayed} delayed")
    if cancelled:
        parts.append(f"{cancelled} cancelled")

    return ", ".join(parts) if parts else "No trains"


class TestStatusHierarchy:
    """Test cases for status hierarchy."""

    def test_no_trains_returns_normal(self):
        """Test that no trains returns Normal status."""
        result = calculate_status([], 3, 10, 15)
        assert result == STATUS_NORMAL

    def test_on_time_returns_normal(self):
        """Test that on-time train returns Normal status."""
        departures = [{"is_cancelled": False, "delay_minutes": 0}]
        result = calculate_status(departures, 3, 10, 15)
        assert result == STATUS_NORMAL

    def test_delay_below_minor_threshold_returns_normal(self):
        """Test delay below minor threshold returns Normal."""
        departures = [{"is_cancelled": False, "delay_minutes": 2}]
        result = calculate_status(departures, 3, 10, 15)
        assert result == STATUS_NORMAL

    def test_delay_at_minor_threshold_returns_minor(self):
        """Test delay at minor threshold returns Minor Delays."""
        departures = [{"is_cancelled": False, "delay_minutes": 3}]
        result = calculate_status(departures, 3, 10, 15)
        assert result == STATUS_MINOR

    def test_delay_above_minor_returns_minor(self):
        """Test delay above minor threshold returns Minor."""
        departures = [{"is_cancelled": False, "delay_minutes": 5}]
        result = calculate_status(departures, 3, 10, 15)
        assert result == STATUS_MINOR

    def test_delay_at_major_threshold_returns_major(self):
        """Test delay at major threshold returns Major Delays."""
        departures = [{"is_cancelled": False, "delay_minutes": 10}]
        result = calculate_status(departures, 3, 10, 15)
        assert result == STATUS_MAJOR

    def test_delay_above_major_returns_major(self):
        """Test delay above major threshold returns Major."""
        departures = [{"is_cancelled": False, "delay_minutes": 12}]
        result = calculate_status(departures, 3, 10, 15)
        assert result == STATUS_MAJOR

    def test_delay_at_severe_threshold_returns_severe(self):
        """Test delay at severe threshold returns Severe Disruption."""
        departures = [{"is_cancelled": False, "delay_minutes": 15}]
        result = calculate_status(departures, 3, 10, 15)
        assert result == STATUS_SEVERE

    def test_delay_above_severe_returns_severe(self):
        """Test delay above severe threshold returns Severe."""
        departures = [{"is_cancelled": False, "delay_minutes": 20}]
        result = calculate_status(departures, 3, 10, 15)
        assert result == STATUS_SEVERE

    def test_cancelled_returns_critical(self):
        """Test that cancelled train returns Critical status."""
        departures = [{"is_cancelled": True, "delay_minutes": 0}]
        result = calculate_status(departures, 3, 10, 15)
        assert result == STATUS_CRITICAL

    def test_cancelled_overrides_delay(self):
        """Test that cancelled overrides any delay."""
        departures = [
            {"is_cancelled": True, "delay_minutes": 0},
            {"is_cancelled": False, "delay_minutes": 2},
        ]
        result = calculate_status(departures, 3, 10, 15)
        assert result == STATUS_CRITICAL

    def test_max_delay_from_multiple_trains(self):
        """Test that max delay is used from multiple trains."""
        departures = [
            {"is_cancelled": False, "delay_minutes": 2},
            {"is_cancelled": False, "delay_minutes": 12},
            {"is_cancelled": False, "delay_minutes": 5},
        ]
        result = calculate_status(departures, 3, 10, 15)
        assert result == STATUS_MAJOR


class TestSummaryCalculation:
    """Test cases for summary string generation."""

    def test_no_trains_returns_no_trains(self):
        """Test that no trains returns 'No trains'."""
        result = calculate_summary([], 3)
        assert result == "No trains"

    def test_single_on_time_returns_on_time(self):
        """Test single on-time train."""
        departures = [{"is_cancelled": False, "delay_minutes": 0}]
        result = calculate_summary(departures, 3)
        assert result == "1 on time"

    def test_single_delayed_returns_delayed(self):
        """Test single delayed train."""
        departures = [{"is_cancelled": False, "delay_minutes": 5}]
        result = calculate_summary(departures, 3)
        assert result == "1 delayed"

    def test_single_cancelled_returns_cancelled(self):
        """Test single cancelled train."""
        departures = [{"is_cancelled": True, "delay_minutes": 0}]
        result = calculate_summary(departures, 3)
        assert result == "1 cancelled"

    def test_multiple_on_time(self):
        """Test multiple on-time trains."""
        departures = [
            {"is_cancelled": False, "delay_minutes": 0},
            {"is_cancelled": False, "delay_minutes": 1},
        ]
        result = calculate_summary(departures, 3)
        assert result == "2 on time"

    def test_mixed_on_time_and_delayed(self):
        """Test mixed on-time and delayed trains."""
        departures = [
            {"is_cancelled": False, "delay_minutes": 0},
            {"is_cancelled": False, "delay_minutes": 5},
        ]
        result = calculate_summary(departures, 3)
        assert result == "1 on time, 1 delayed"

    def test_all_three_categories(self):
        """Test all three categories present."""
        departures = [
            {"is_cancelled": False, "delay_minutes": 0},
            {"is_cancelled": False, "delay_minutes": 5},
            {"is_cancelled": True, "delay_minutes": 0},
        ]
        result = calculate_summary(departures, 3)
        assert result == "1 on time, 1 delayed, 1 cancelled"

    def test_threshold_respected(self):
        """Test that minor threshold is respected."""
        # At threshold (3) should be delayed
        departures = [{"is_cancelled": False, "delay_minutes": 3}]
        result = calculate_summary(departures, 3)
        assert result == "1 delayed"

        # Below threshold should be on time
        departures = [{"is_cancelled": False, "delay_minutes": 2}]
        result = calculate_summary(departures, 3)
        assert result == "1 on time"


class TestCustomThresholds:
    """Test with custom threshold values."""

    def test_custom_minor_threshold(self):
        """Test with custom minor threshold."""
        departures = [{"is_cancelled": False, "delay_minutes": 5}]
        # With threshold at 5, 5 minutes is at threshold = delayed
        result = calculate_status(departures, 5, 10, 15)
        assert result == STATUS_MINOR

    def test_custom_major_threshold(self):
        """Test with custom major threshold."""
        departures = [{"is_cancelled": False, "delay_minutes": 8}]
        # With major at 8, 8 minutes is at threshold = major
        result = calculate_status(departures, 3, 8, 15)
        assert result == STATUS_MAJOR


class TestSummaryAllTrainsTrainNumber:
    """Test that all_trains uses integer train_number and preserves product name as service_id."""

    def test_train_number_is_integer_index(self):
        """train_number in all_trains should be 1-based integer index, not product name."""
        origin, destination = _make_origin_destination()
        deps = [
            _make_departure(train_number="RE 4632"),
            _make_departure(train_number="RB 5101"),
            _make_departure(train_number="IC 407"),
        ]
        coordinator = _make_coordinator(deps)
        sensor = CFLCommuteSummarySensor(
            coordinator=coordinator,
            commute_name="test",
            origin=origin,
            destination=destination,
            num_trains=3,
            minor_threshold=3,
            major_threshold=10,
            severe_threshold=15,
        )
        all_trains = sensor.extra_state_attributes["all_trains"]
        assert all_trains[0]["train_number"] == 1
        assert all_trains[1]["train_number"] == 2
        assert all_trains[2]["train_number"] == 3

    def test_service_id_preserves_product_name(self):
        """service_id in all_trains should contain the original product name string."""
        origin, destination = _make_origin_destination()
        deps = [
            _make_departure(train_number="RE 4632"),
            _make_departure(train_number="RB 5101"),
        ]
        coordinator = _make_coordinator(deps)
        sensor = CFLCommuteSummarySensor(
            coordinator=coordinator,
            commute_name="test",
            origin=origin,
            destination=destination,
            num_trains=3,
            minor_threshold=3,
            major_threshold=10,
            severe_threshold=15,
        )
        all_trains = sensor.extra_state_attributes["all_trains"]
        assert all_trains[0]["service_id"] == "RE 4632"
        assert all_trains[1]["service_id"] == "RB 5101"

    def test_train_number_int_not_string(self):
        """train_number must be int, not string, for entity ID resolution."""
        origin, destination = _make_origin_destination()
        deps = [_make_departure(train_number="RE 4632")]
        coordinator = _make_coordinator(deps)
        sensor = CFLCommuteSummarySensor(
            coordinator=coordinator,
            commute_name="test",
            origin=origin,
            destination=destination,
            num_trains=3,
            minor_threshold=3,
            major_threshold=10,
            severe_threshold=15,
        )
        all_trains = sensor.extra_state_attributes["all_trains"]
        assert isinstance(all_trains[0]["train_number"], int)


class TestSummaryAllTrainsJson:
    """Test that all_trains_json is a JSON string matching all_trains."""

    def test_all_trains_json_matches_all_trains(self):
        """all_trains_json should parse back to the same data as all_trains."""
        origin, destination = _make_origin_destination()
        deps = [
            _make_departure(train_number="RE 4632"),
            _make_departure(train_number="RB 5101"),
        ]
        coordinator = _make_coordinator(deps)
        sensor = CFLCommuteSummarySensor(
            coordinator=coordinator,
            commute_name="test",
            origin=origin,
            destination=destination,
            num_trains=3,
            minor_threshold=3,
            major_threshold=10,
            severe_threshold=15,
        )
        attrs = sensor.extra_state_attributes
        parsed = json.loads(attrs["all_trains_json"])
        assert parsed == attrs["all_trains"]


class TestNextTrainTrainNumber:
    """Test that NextTrain sensor uses train_number=1 and service_id for product name."""

    def test_train_number_is_one(self):
        """Next train sensor should always have train_number=1."""
        origin, destination = _make_origin_destination()
        deps = [_make_departure(train_number="RE 4632")]
        coordinator = _make_coordinator(deps)
        sensor = CFLCommuteNextTrainSensor(
            coordinator=coordinator,
            commute_name="test",
            origin=origin,
            destination=destination,
            num_trains=3,
            minor_threshold=3,
            major_threshold=10,
            severe_threshold=15,
        )
        attrs = sensor.extra_state_attributes
        assert attrs["train_number"] == 1
        assert isinstance(attrs["train_number"], int)

    def test_service_id_has_product_name(self):
        """service_id should contain the Departure.train_number product name."""
        origin, destination = _make_origin_destination()
        deps = [_make_departure(train_number="RE 4632")]
        coordinator = _make_coordinator(deps)
        sensor = CFLCommuteNextTrainSensor(
            coordinator=coordinator,
            commute_name="test",
            origin=origin,
            destination=destination,
            num_trains=3,
            minor_threshold=3,
            major_threshold=10,
            severe_threshold=15,
        )
        attrs = sensor.extra_state_attributes
        assert attrs["service_id"] == "RE 4632"


class TestTrainSensorTrainNumber:
    """Test that individual train sensors use integer train_number matching entity index."""

    def test_train_1_has_train_number_1(self):
        """Train 1 sensor should have train_number=1."""
        origin, destination = _make_origin_destination()
        deps = [
            _make_departure(train_number="RE 4632"),
            _make_departure(train_number="RB 5101"),
        ]
        coordinator = _make_coordinator(deps)
        sensor = CFLCommuteTrainSensor(
            coordinator=coordinator,
            commute_name="test",
            origin=origin,
            destination=destination,
            num_trains=2,
            minor_threshold=3,
            major_threshold=10,
            severe_threshold=15,
            train_number=1,
        )
        attrs = sensor.extra_state_attributes
        assert attrs["train_number"] == 1
        assert isinstance(attrs["train_number"], int)
        assert attrs["service_id"] == "RE 4632"

    def test_train_2_has_train_number_2(self):
        """Train 2 sensor should have train_number=2."""
        origin, destination = _make_origin_destination()
        deps = [
            _make_departure(train_number="RE 4632"),
            _make_departure(train_number="RB 5101"),
        ]
        coordinator = _make_coordinator(deps)
        sensor = CFLCommuteTrainSensor(
            coordinator=coordinator,
            commute_name="test",
            origin=origin,
            destination=destination,
            num_trains=2,
            minor_threshold=3,
            major_threshold=10,
            severe_threshold=15,
            train_number=2,
        )
        attrs = sensor.extra_state_attributes
        assert attrs["train_number"] == 2
        assert attrs["service_id"] == "RB 5101"

    def test_train_number_matches_entity_id_convention(self):
        """train_number should match the N in sensor.{name}_train_N entity ID."""
        origin, destination = _make_origin_destination()
        deps = [
            _make_departure(train_number="RE 4632"),
            _make_departure(train_number="RB 5101"),
            _make_departure(train_number="IC 407"),
        ]
        coordinator = _make_coordinator(deps)
        for idx in range(1, 4):
            sensor = CFLCommuteTrainSensor(
                coordinator=coordinator,
                commute_name="test",
                origin=origin,
                destination=destination,
                num_trains=3,
                minor_threshold=3,
                major_threshold=10,
                severe_threshold=15,
                train_number=idx,
            )
            assert sensor.extra_state_attributes["train_number"] == idx

    def test_no_departures_returns_base_attrs(self):
        """When no departures, train-specific attributes should not be present."""
        origin, destination = _make_origin_destination()
        coordinator = _make_coordinator([])
        sensor = CFLCommuteTrainSensor(
            coordinator=coordinator,
            commute_name="test",
            origin=origin,
            destination=destination,
            num_trains=3,
            minor_threshold=3,
            major_threshold=10,
            severe_threshold=15,
            train_number=1,
        )
        attrs = sensor.extra_state_attributes
        assert "train_number" not in attrs
        assert "service_id" not in attrs
