"""Tests for platform async_setup_entry reading the effective config.

Regression tests for the bug where Options-flow changes (stored in
config_entry.options) were ignored because platforms read settings from
the immutable config_entry.data instead of the merged
{**data, **options} config computed in __init__.async_setup_entry.
"""

from unittest.mock import MagicMock

import pytest

from custom_components.cfl_commute.binary_sensor import (
    CFLCommuteDisruptionSensor,
    async_setup_entry as binary_sensor_async_setup_entry,
)
from custom_components.cfl_commute.const import DOMAIN
from custom_components.cfl_commute.sensor import (
    CFLCommuteHistoricalDelaysSensor,
    CFLCommuteHistoricalReliabilitySensor,
    CFLCommuteNextTrainSensor,
    CFLCommuteStatusSensor,
    CFLCommuteSummarySensor,
    CFLCommuteTrainSensor,
    async_setup_entry as sensor_async_setup_entry,
)

BASE_DATA = {
    "api_key": "test_key",
    "origin": {"id": "200426002", "name": "Luxembourg"},
    "destination": {"id": "200426001", "name": "Esch-sur-Alzette"},
    "commute_name": "Test Commute",
    "time_window": 60,
    "num_trains": 3,
    "minor_threshold": 3,
    "major_threshold": 10,
    "severe_threshold": 15,
    "night_updates": False,
}

ENTRY_ID = "test_entry"


def _make_entry(data: dict, options: dict) -> MagicMock:
    """Build a config entry mock with the given data and options."""
    entry = MagicMock()
    entry.entry_id = ENTRY_ID
    entry.data = data
    entry.options = options
    return entry


def _make_hass(data: dict, options: dict) -> MagicMock:
    """Build a hass mock pre-populated exactly as __init__.async_setup_entry does."""
    hass = MagicMock()
    hass.data = {
        DOMAIN: {
            ENTRY_ID: {
                "coordinator": MagicMock(),
                "config": {**data, **options},
            }
        }
    }
    return hass


class TestSensorSetupEffectiveConfig:
    """Sensor platform reads num_trains/thresholds from effective config."""

    @pytest.mark.asyncio
    async def test_num_trains_increase_creates_fourth_train_sensor(self):
        """Regression: changing num_trains 3->4 via options must create train_4."""
        options = {"num_trains": 4}
        hass = _make_hass(BASE_DATA, options)
        entry = _make_entry(BASE_DATA, options)
        added = []

        await sensor_async_setup_entry(hass, entry, added.extend)

        train_sensors = [s for s in added if isinstance(s, CFLCommuteTrainSensor)]
        assert [s._train_number for s in train_sensors] == [1, 2, 3, 4]
        assert all(s._num_trains == 4 for s in train_sensors)

    @pytest.mark.asyncio
    async def test_num_trains_reduction_creates_fewer_train_sensors(self):
        """Symmetric case: reducing num_trains 4->2 via options creates only 2."""
        data = {**BASE_DATA, "num_trains": 4}
        options = {"num_trains": 2}
        hass = _make_hass(data, options)
        entry = _make_entry(data, options)
        added = []

        await sensor_async_setup_entry(hass, entry, added.extend)

        train_sensors = [s for s in added if isinstance(s, CFLCommuteTrainSensor)]
        assert [s._train_number for s in train_sensors] == [1, 2]
        assert all(s._num_trains == 2 for s in train_sensors)

    @pytest.mark.asyncio
    async def test_options_override_data_for_name_and_thresholds(self):
        """Options-flow threshold/commute_name changes must reach the sensors."""
        options = {
            "commute_name": "Renamed Commute",
            "num_trains": 4,
            "minor_threshold": 5,
            "major_threshold": 12,
            "severe_threshold": 20,
        }
        hass = _make_hass(BASE_DATA, options)
        entry = _make_entry(BASE_DATA, options)
        added = []

        await sensor_async_setup_entry(hass, entry, added.extend)

        summary = next(s for s in added if isinstance(s, CFLCommuteSummarySensor))
        assert summary._commute_name == "Renamed Commute"
        assert summary._num_trains == 4
        assert summary._minor_threshold == 5
        assert summary._major_threshold == 12
        assert summary._severe_threshold == 20

    @pytest.mark.asyncio
    async def test_data_values_used_when_options_empty(self):
        """Without options, setup falls back to the initial data values."""
        hass = _make_hass(BASE_DATA, {})
        entry = _make_entry(BASE_DATA, {})
        added = []

        await sensor_async_setup_entry(hass, entry, added.extend)

        assert (
            len(added) == 8
        )  # summary + status + next_train + 3 trains + 2 historical
        assert sum(1 for s in added if isinstance(s, CFLCommuteTrainSensor)) == 3
        assert any(isinstance(s, CFLCommuteSummarySensor) for s in added)
        assert any(isinstance(s, CFLCommuteStatusSensor) for s in added)
        assert any(isinstance(s, CFLCommuteNextTrainSensor) for s in added)
        assert any(isinstance(s, CFLCommuteHistoricalReliabilitySensor) for s in added)
        assert any(isinstance(s, CFLCommuteHistoricalDelaysSensor) for s in added)


class TestBinarySensorSetupEffectiveConfig:
    """Binary sensor platform reads settings from effective config."""

    @pytest.mark.asyncio
    async def test_options_values_reach_disruption_sensor(self):
        """Regression: options-flow changes must reach the disruption sensor."""
        options = {
            "commute_name": "Renamed Commute",
            "num_trains": 4,
            "minor_threshold": 5,
            "major_threshold": 12,
            "severe_threshold": 20,
        }
        hass = _make_hass(BASE_DATA, options)
        entry = _make_entry(BASE_DATA, options)
        added = []

        await binary_sensor_async_setup_entry(hass, entry, added.extend)

        assert len(added) == 1
        sensor = added[0]
        assert isinstance(sensor, CFLCommuteDisruptionSensor)
        assert sensor._commute_name == "Renamed Commute"
        assert sensor._num_trains == 4
        assert sensor._minor_threshold == 5
        assert sensor._major_threshold == 12
        assert sensor._severe_threshold == 20

    @pytest.mark.asyncio
    async def test_data_values_used_when_options_empty(self):
        """Without options, binary sensor setup falls back to the data values."""
        hass = _make_hass(BASE_DATA, {})
        entry = _make_entry(BASE_DATA, {})
        added = []

        await binary_sensor_async_setup_entry(hass, entry, added.extend)

        assert len(added) == 1
        sensor = added[0]
        assert sensor._commute_name == "Test Commute"
        assert sensor._num_trains == 3
        assert sensor._minor_threshold == 3
        assert sensor._major_threshold == 10
        assert sensor._severe_threshold == 15
