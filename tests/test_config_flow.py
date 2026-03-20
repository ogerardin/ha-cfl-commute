"""Tests for config flow."""

import pytest
import voluptuous as vol
from unittest.mock import AsyncMock, MagicMock, patch
from custom_components.cfl_commute.config_flow import (
    CFLCommuteConfigFlow,
    CONFIG_SCHEMA,
)
from custom_components.cfl_commute.const import (
    CONF_API_KEY,
    CONF_COMMUTE_NAME,
    CONF_TIME_WINDOW,
    CONF_NUM_TRAINS,
    DEFAULT_TIME_WINDOW,
    DEFAULT_NUM_TRAINS,
)


class TestConfigSchema:
    """Test configuration schemas."""

    def test_config_schema_requires_api_key(self):
        """Test that API key is required."""
        with pytest.raises(vol.Invalid):
            CONFIG_SCHEMA({})

    def test_config_schema_accepts_valid_api_key(self):
        """Test that valid API key is accepted."""
        result = CONFIG_SCHEMA({"api_key": "test_key_123"})
        assert result["api_key"] == "test_key_123"


class TestConfigFlowInit:
    """Test config flow initialization."""

    def test_config_flow_initial_state(self):
        """Test initial state of config flow."""
        flow = CFLCommuteConfigFlow()
        assert flow._api_key == ""
        assert flow._origin_station == {}
        assert flow._destination_station == {}
        assert flow._client is None

    def test_config_flow_has_version(self):
        """Test config flow has version."""
        flow = CFLCommuteConfigFlow()
        assert flow.VERSION == 1


class TestCommuteNameGeneration:
    """Test commute name generation."""

    def test_default_commute_name_format(self):
        """Test default commute name format."""
        origin = "Luxembourg"
        destination = "Esch-sur-Alzette"
        expected = "Luxembourg → Esch-sur-Alzette"
        assert f"{origin} → {destination}" == expected
