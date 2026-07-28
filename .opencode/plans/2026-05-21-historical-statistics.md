# Historical Statistics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port upstream V1.1.5 historical performance tracking (persistent daily stats, historical sensor entities, historical stats on summary sensor, reverse-route stats, get_historical_raw_data service) from `adamf83/my-rail-commute` to this CFL Commute fork.

**Architecture:** Adapt upstream's `CommuteStatisticsStore` (HA `Store`-backed) to work with CFL's `Departure` dataclass model. Add two new sensor entities, enrich the summary sensor's attributes, add a HA service for raw data access. Keep coordinator returning `list[Departure]` (no breaking change). New code follows existing CFL fork patterns (state property, not native_value).

**Tech Stack:** Python 3.14, Home Assistant, pytest-asyncio, voluptuous

**Non-regression:** All 92 existing tests must pass before and after. Existing sensor data formats unchanged.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `custom_components/cfl_commute/const.py` | Modify | Add stats-related constants (ATTR_*, STATUS_*, STORAGE_VERSION, STATS_RETENTION_DAYS) |
| `custom_components/cfl_commute/statistics.py` | Create | `CFLCommuteStatisticsStore` — persistent daily stats using HA's `Store` |
| `custom_components/cfl_commute/coordinator.py` | Modify | Add `stats_store` attribute, record observation on successful update |
| `custom_components/cfl_commute/__init__.py` | Modify | Initialize `CFLCommuteStatisticsStore`, wire to coordinator, register `get_historical_raw_data` service |
| `custom_components/cfl_commute/sensor.py` | Modify | Add two new historical sensor classes, extend SummarySensor with historical + reverse-route attrs |
| `custom_components/cfl_commute/services.yaml` | Create | Define `get_historical_raw_data` service |
| `tests/test_statistics.py` | Create | Tests for `CFLCommuteStatisticsStore` (ported from upstream) |
| `tests/test_sensor_historical.py` | Create | Tests for new historical sensors + summary sensor historical stats |

---

## Design Decisions

1. **No breaking changes to coordinator return type.** The CFL coordinator continues to return `list[Departure]`. Stats recording builds the internal `parsed_data` dict from the departure list, then calls `stats_store.async_record_observation()`.

2. **Attribute names match upstream.** Historical sensor attrs use the same names as `my-rail-commute` (e.g., `on_time_pct_today`, `on_time_pct_7day`, `worst_day`, `daily_breakdown`).

3. **Threshold vs raw delay for stats.** The upstream historical stats use raw delay (delay > 0 = delayed), NOT user-configurable thresholds. This creates a slight difference from the CFL summary sensor which uses thresholds. This matches upstream behavior.

4. **Sensor entity patterns follow CFL fork.** Use `state` property (not `native_value`), `name` property (not `_attr_name`), for consistency with existing CFL sensor code.

5. **Summary sensor's historical stats omit `daily_breakdown`.** Following upstream fix (PR #138) to stay within HA's 16 KB attribute limit. `daily_breakdown` is only on `HistoricalReliabilitySensor`.

6. **Reverse-route stats lookup adapts to CFL's `hass.data[DOMAIN]` structure.** The CFL fork stores `{"coordinator": ..., "api": ..., "config": ...}` per entry, not the coordinator directly. Reverse lookup extracts coordinator from the nested dict.

---

### Task 1: Add constants to const.py

**Files:**
- Modify: `custom_components/cfl_commute/const.py`

- [ ] **Step 1: Add stats-related status constants after existing TRAIN_* constants**

Add these lowercase status strings (used for internal parsed_data in stats recording, distinct from existing human-readable TRAIN_*):

```python
# Internal status values for statistics recording
STATUS_ON_TIME = "on_time"
STATUS_DELAYED = "delayed"
STATUS_CANCELLED = "cancelled"
```

Add these storage constants:

```python
# Historical statistics storage
STORAGE_VERSION = 1
STATS_RETENTION_DAYS = 90
```

Add these attribute name constants at the end of the file:

```python
# Attribute names for historical sensors
ATTR_ON_TIME_PCT_TODAY = "on_time_pct_today"
ATTR_ON_TIME_PCT_7D = "on_time_pct_7day"
ATTR_ON_TIME_PCT_30D = "on_time_pct_30day"
ATTR_AVG_DELAY_TODAY = "avg_delay_today"
ATTR_AVG_DELAY_7D = "avg_delay_7day"
ATTR_WORST_DAY = "worst_day"
ATTR_BEST_DAY = "best_day"
ATTR_TOTAL_OBSERVATIONS_TODAY = "total_observations_today"
ATTR_ON_TIME_COUNT_TODAY = "on_time_count_today"
ATTR_DELAYED_COUNT_TODAY = "delayed_count_today"
ATTR_CANCELLED_COUNT_TODAY = "cancelled_count_today"
ATTR_DAILY_BREAKDOWN = "daily_breakdown"

# Reverse-route stats attributes
ATTR_REVERSE_ON_TIME_PCT_TODAY = "reverse_on_time_pct_today"
ATTR_REVERSE_ON_TIME_PCT_7D = "reverse_on_time_pct_7day"
ATTR_REVERSE_ON_TIME_PCT_30D = "reverse_on_time_pct_30day"
ATTR_REVERSE_AVG_DELAY_7D = "reverse_avg_delay_7day"
ATTR_REVERSE_WORST_DAY = "reverse_worst_day"
ATTR_REVERSE_BEST_DAY = "reverse_best_day"

# Service name
SERVICE_GET_HISTORICAL_RAW_DATA = "get_historical_raw_data"
```

- [ ] **Step 2: Run tests to check no regressions**

Run: `source .venv/bin/activate && pytest tests/ -v --tb=short`
Expected: 92 passed (same as baseline)

- [ ] **Step 3: Commit**

```bash
git add custom_components/cfl_commute/const.py
git commit -m "feat: add constants for historical statistics tracking"
```

---

### Task 2: Create CFLCommuteStatisticsStore (statistics.py)

**Files:**
- Create: `custom_components/cfl_commute/statistics.py`
- Test: `tests/test_statistics.py`

This is the core persistence layer, adapted from upstream's `CommuteStatisticsStore`. Key adaptation: the upstream receives a `parsed_data` dict; the CFL version does the same (the coordinator builds this dict from `list[Departure]` before calling).

- [ ] **Step 1: Create `custom_components/cfl_commute/statistics.py`**

```python
"""Persistent daily statistics storage for CFL Commute integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    STATS_RETENTION_DAYS,
    STORAGE_VERSION,
    STATUS_DELAYED,
)

_LOGGER = logging.getLogger(__name__)


class CFLCommuteStatisticsStore:
    """Manages persistent daily commute statistics using HA's Store."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, STORAGE_VERSION, f"{DOMAIN}_{entry_id}_stats")
        self._data: dict[str, Any] = {}

    async def async_load(self) -> None:
        """Load persisted data from storage."""
        raw = await self._store.async_load()
        if raw is None:
            self._data = {}
        else:
            self._data = raw.get("days", {})
        self._prune_old_entries()
        _LOGGER.debug("Loaded %d days of historical stats", len(self._data))

    async def async_record_observation(self, parsed_data: dict[str, Any]) -> None:
        """Accumulate today's observation from a coordinator update and persist."""
        if parsed_data.get("services_tracked", 0) == 0:
            _LOGGER.debug("Skipping stats recording: no services tracked in this update")
            return

        today_key = dt_util.now().date().isoformat()
        day = self._data.get(today_key, {
            "on_time_count": 0,
            "delayed_count": 0,
            "cancelled_count": 0,
            "total_observations": 0,
            "total_delay_minutes": 0,
        })

        on_time = parsed_data.get("on_time_count", 0)
        delayed = parsed_data.get("delayed_count", 0)
        cancelled = parsed_data.get("cancelled_count", 0)
        obs = on_time + delayed + cancelled

        total_delay = sum(
            s.get("delay_minutes", 0)
            for s in parsed_data.get("services", [])
            if s.get("status") == STATUS_DELAYED and not s.get("is_cancelled", False)
        )

        day["on_time_count"] += on_time
        day["delayed_count"] += delayed
        day["cancelled_count"] += cancelled
        day["total_observations"] += obs
        day["total_delay_minutes"] += total_delay

        total_obs = day["total_observations"]
        day["on_time_pct"] = round(day["on_time_count"] / total_obs * 100, 2) if total_obs > 0 else 0.0
        day["avg_delay_minutes"] = (
            round(day["total_delay_minutes"] / day["delayed_count"], 2)
            if day["delayed_count"] > 0
            else 0.0
        )

        self._data[today_key] = day
        self._prune_old_entries()
        await self._store.async_save({"version": STORAGE_VERSION, "days": self._data})
        _LOGGER.debug(
            "Recorded stats for %s: on_time=%d delayed=%d cancelled=%d",
            today_key, on_time, delayed, cancelled,
        )

    def get_today_stats(self) -> dict[str, Any]:
        """Return today's accumulated stats, or an empty dict if no data yet."""
        return self._data.get(dt_util.now().date().isoformat(), {})

    def get_rolling_stats(self, days: int) -> dict[str, Any]:
        """Return aggregated stats across the last `days` calendar days (today included)."""
        today = dt_util.now().date()
        window = [(today - timedelta(days=i)).isoformat() for i in range(days)]
        days_with_data = [d for d in window if d in self._data]

        if not days_with_data:
            return {"on_time_pct": None, "avg_delay_minutes": None, "days_with_data": 0}

        total_on_time = sum(self._data[d]["on_time_count"] for d in days_with_data)
        total_obs = sum(self._data[d]["total_observations"] for d in days_with_data)
        total_delayed = sum(self._data[d]["delayed_count"] for d in days_with_data)
        total_delay_min = sum(self._data[d]["total_delay_minutes"] for d in days_with_data)

        return {
            "on_time_pct": round(total_on_time / total_obs * 100, 1) if total_obs > 0 else None,
            "avg_delay_minutes": round(total_delay_min / total_delayed, 1) if total_delayed > 0 else None,
            "days_with_data": len(days_with_data),
        }

    def get_best_and_worst_days(self, days: int = 30) -> dict[str, Any]:
        """Return worst/best day (by on-time %) across the last `days` calendar days."""
        today = dt_util.now().date()
        window = [(today - timedelta(days=i)).isoformat() for i in range(days)]
        candidates = {d: self._data[d] for d in window if d in self._data and self._data[d].get("total_observations", 0) > 0}

        if not candidates:
            return {"worst_day": None, "best_day": None}

        worst = min(candidates, key=lambda d: candidates[d].get("on_time_pct", 100))
        best = max(candidates, key=lambda d: candidates[d].get("on_time_pct", 0))

        return {
            "worst_day": {
                "date": worst,
                "on_time_pct": candidates[worst].get("on_time_pct"),
                "avg_delay_minutes": candidates[worst].get("avg_delay_minutes"),
            },
            "best_day": {
                "date": best,
                "on_time_pct": candidates[best].get("on_time_pct"),
                "avg_delay_minutes": candidates[best].get("avg_delay_minutes"),
            },
        }

    def get_daily_breakdown(self, days: int = 30) -> list[dict[str, Any]]:
        """Return per-day stats for last N calendar days, oldest first."""
        today = dt_util.now().date()
        result = []
        for i in range(days - 1, -1, -1):
            date_str = (today - timedelta(days=i)).isoformat()
            day = self._data.get(date_str)
            result.append({
                "date": date_str,
                "on_time_pct": day.get("on_time_pct") if day else None,
                "avg_delay_minutes": day.get("avg_delay_minutes") if day else None,
                "total_observations": day.get("total_observations", 0) if day else 0,
            })
        return result

    def get_raw_data(self) -> dict[str, Any]:
        """Return a copy of all stored daily stats records."""
        return dict(self._data)

    def _prune_old_entries(self) -> None:
        """Remove entries older than STATS_RETENTION_DAYS."""
        cutoff = (dt_util.now().date() - timedelta(days=STATS_RETENTION_DAYS)).isoformat()
        stale = [key for key in self._data if key < cutoff]
        for key in stale:
            del self._data[key]
        if stale:
            _LOGGER.debug("Pruned %d stale stats entries (older than %s)", len(stale), cutoff)
```

- [ ] **Step 2: Create `tests/test_statistics.py`**

```python
"""Tests for CFLCommuteStatisticsStore."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.cfl_commute.statistics import CFLCommuteStatisticsStore


def _make_store(load_return=None):
    """Return a CFLCommuteStatisticsStore with a mocked HA Store."""
    hass = MagicMock()
    with patch(
        "custom_components.cfl_commute.statistics.Store"
    ) as MockStore:
        instance = MockStore.return_value
        instance.async_load = AsyncMock(return_value=load_return)
        instance.async_save = AsyncMock(return_value=None)
        store = CFLCommuteStatisticsStore(hass, "test_entry_id")
        store._store = instance
    return store


def _parsed_data(on_time=2, delayed=1, cancelled=0, services=None):
    """Build a minimal parsed_data dict as the coordinator produces."""
    if services is None:
        services = []
        for _ in range(on_time):
            services.append({"status": "on_time", "delay_minutes": 0, "is_cancelled": False})
        for dm in range(delayed):
            services.append({"status": "delayed", "delay_minutes": 5 * (dm + 1), "is_cancelled": False})
        for _ in range(cancelled):
            services.append({"status": "cancelled", "delay_minutes": 0, "is_cancelled": True})
    return {
        "on_time_count": on_time,
        "delayed_count": delayed,
        "cancelled_count": cancelled,
        "services_tracked": on_time + delayed + cancelled,
        "services": services,
    }


@pytest.mark.asyncio
async def test_load_no_data():
    """async_load with no persisted data initialises empty dict."""
    store = _make_store(load_return=None)
    await store.async_load()
    assert store._data == {}


@pytest.mark.asyncio
async def test_load_existing_data():
    """async_load restores previously persisted data."""
    existing = {"days": {"2026-05-17": {"on_time_count": 5, "delayed_count": 1,
                                         "cancelled_count": 0, "total_observations": 6,
                                         "total_delay_minutes": 10,
                                         "on_time_pct": 83.33, "avg_delay_minutes": 10.0}}}
    store = _make_store(load_return=existing)
    await store.async_load()
    assert "2026-05-17" in store._data
    assert store._data["2026-05-17"]["on_time_count"] == 5


@pytest.mark.asyncio
async def test_record_new_day():
    """First observation of the day creates a new entry and persists."""
    store = _make_store()
    await store.async_load()

    today = date.today().isoformat()
    with patch("custom_components.cfl_commute.statistics.dt_util") as mock_dt:
        mock_dt.now.return_value.date.return_value = date.fromisoformat(today)
        await store.async_record_observation(_parsed_data(on_time=2, delayed=1, cancelled=0))

    assert today in store._data
    day = store._data[today]
    assert day["on_time_count"] == 2
    assert day["delayed_count"] == 1
    assert day["cancelled_count"] == 0
    assert day["total_observations"] == 3
    store._store.async_save.assert_called_once()


@pytest.mark.asyncio
async def test_record_same_day_accumulates():
    """Multiple observations on the same day accumulate counts."""
    store = _make_store()
    await store.async_load()
    today = "2026-05-17"

    with patch("custom_components.cfl_commute.statistics.dt_util") as mock_dt:
        mock_dt.now.return_value.date.return_value = date.fromisoformat(today)
        await store.async_record_observation(_parsed_data(on_time=2, delayed=1, cancelled=0))
        await store.async_record_observation(_parsed_data(on_time=1, delayed=0, cancelled=1))

    day = store._data[today]
    assert day["on_time_count"] == 3
    assert day["delayed_count"] == 1
    assert day["cancelled_count"] == 1
    assert day["total_observations"] == 5


@pytest.mark.asyncio
async def test_record_zero_services_skipped():
    """Observations with zero services_tracked are silently skipped."""
    store = _make_store()
    await store.async_load()
    today = "2026-05-17"

    with patch("custom_components.cfl_commute.statistics.dt_util") as mock_dt:
        mock_dt.now.return_value.date.return_value = date.fromisoformat(today)
        await store.async_record_observation({"services_tracked": 0, "on_time_count": 0,
                                               "delayed_count": 0, "cancelled_count": 0,
                                               "services": []})

    assert today not in store._data
    store._store.async_save.assert_not_called()


def test_prune_removes_old_entries():
    """_prune_old_entries removes dates older than STATS_RETENTION_DAYS."""
    store = _make_store()
    store._data = {}

    cutoff_date = date.today() - timedelta(days=91)
    recent_date = date.today().isoformat()
    old_date = cutoff_date.isoformat()

    store._data[old_date] = {"on_time_count": 1, "total_observations": 1}
    store._data[recent_date] = {"on_time_count": 3, "total_observations": 3}

    with patch("custom_components.cfl_commute.statistics.dt_util") as mock_dt:
        mock_dt.now.return_value.date.return_value = date.today()
        store._prune_old_entries()

    assert old_date not in store._data
    assert recent_date in store._data


def test_get_rolling_stats_no_data():
    """get_rolling_stats returns None values when there is no data."""
    store = _make_store()
    result = store.get_rolling_stats(7)
    assert result["on_time_pct"] is None
    assert result["avg_delay_minutes"] is None
    assert result["days_with_data"] == 0


def test_get_rolling_stats_with_data():
    """get_rolling_stats aggregates correctly across multiple days."""
    store = _make_store()
    today = date.today()

    store._data = {
        (today - timedelta(days=0)).isoformat(): {
            "on_time_count": 8, "delayed_count": 2, "cancelled_count": 0,
            "total_observations": 10, "total_delay_minutes": 20,
        },
        (today - timedelta(days=1)).isoformat(): {
            "on_time_count": 6, "delayed_count": 4, "cancelled_count": 0,
            "total_observations": 10, "total_delay_minutes": 40,
        },
    }

    with patch("custom_components.cfl_commute.statistics.dt_util") as mock_dt:
        mock_dt.now.return_value.date.return_value = today
        result = store.get_rolling_stats(7)

    assert result["days_with_data"] == 2
    assert result["on_time_pct"] == 70.0  # 14/20 * 100
    assert result["avg_delay_minutes"] == 10.0  # 60 total delay / 6 delayed


def test_get_rolling_stats_excludes_days_outside_window():
    """get_rolling_stats only includes days within the requested window."""
    store = _make_store()
    today = date.today()

    store._data = {
        (today - timedelta(days=2)).isoformat(): {
            "on_time_count": 5, "delayed_count": 0, "cancelled_count": 0,
            "total_observations": 5, "total_delay_minutes": 0,
        },
        (today - timedelta(days=10)).isoformat(): {
            "on_time_count": 1, "delayed_count": 9, "cancelled_count": 0,
            "total_observations": 10, "total_delay_minutes": 90,
        },
    }

    with patch("custom_components.cfl_commute.statistics.dt_util") as mock_dt:
        mock_dt.now.return_value.date.return_value = today
        result = store.get_rolling_stats(7)

    assert result["days_with_data"] == 1
    assert result["on_time_pct"] == 100.0


def test_get_best_and_worst_days_no_data():
    """get_best_and_worst_days returns None values when there is no data."""
    store = _make_store()
    result = store.get_best_and_worst_days(30)
    assert result["worst_day"] is None
    assert result["best_day"] is None


def test_get_best_and_worst_days():
    """get_best_and_worst_days identifies correct best and worst days."""
    store = _make_store()
    today = date.today()

    good_day = (today - timedelta(days=1)).isoformat()
    bad_day = (today - timedelta(days=2)).isoformat()

    store._data = {
        good_day: {"on_time_pct": 95.0, "avg_delay_minutes": 2.0, "total_observations": 10},
        bad_day: {"on_time_pct": 30.0, "avg_delay_minutes": 15.0, "total_observations": 10},
    }

    with patch("custom_components.cfl_commute.statistics.dt_util") as mock_dt:
        mock_dt.now.return_value.date.return_value = today
        result = store.get_best_and_worst_days(30)

    assert result["best_day"]["date"] == good_day
    assert result["worst_day"]["date"] == bad_day


def test_get_today_stats_empty():
    """get_today_stats returns empty dict when no data for today."""
    store = _make_store()
    today = date.today()
    with patch("custom_components.cfl_commute.statistics.dt_util") as mock_dt:
        mock_dt.now.return_value.date.return_value.isoformat.return_value = (
            today - timedelta(days=5)
        ).isoformat()
        result = store.get_today_stats()
    assert result == {}


@pytest.mark.asyncio
async def test_on_time_pct_computed_correctly():
    """on_time_pct is stored and computed correctly after recording."""
    store = _make_store()
    await store.async_load()
    today = "2026-05-17"

    with patch("custom_components.cfl_commute.statistics.dt_util") as mock_dt:
        mock_dt.now.return_value.date.return_value = date.fromisoformat(today)
        await store.async_record_observation(_parsed_data(on_time=3, delayed=1, cancelled=0))

    day = store._data[today]
    assert day["on_time_pct"] == 75.0  # 3/4 * 100
    assert day["avg_delay_minutes"] == 5.0  # 1 delayed service with 5 min delay


def test_get_raw_data_returns_copy():
    """get_raw_data returns all stored daily records as a copy."""
    store = _make_store()
    store._data = {"2026-05-17": {"on_time_count": 5}}
    result = store.get_raw_data()
    assert result == {"2026-05-17": {"on_time_count": 5}}
    result["2026-05-18"] = {}
    assert "2026-05-18" not in store._data


def test_get_raw_data_empty():
    """get_raw_data returns empty dict when no data has been recorded."""
    store = _make_store()
    assert store.get_raw_data() == {}


def test_get_daily_breakdown_returns_30_days():
    """get_daily_breakdown returns 30 entries (one per day), oldest first."""
    store = _make_store()
    today = date.today()
    store._data = {
        (today - timedelta(days=1)).isoformat(): {
            "on_time_pct": 100.0, "avg_delay_minutes": 0.0, "total_observations": 5,
        }
    }

    with patch("custom_components.cfl_commute.statistics.dt_util") as mock_dt:
        mock_dt.now.return_value.date.return_value = today
        result = store.get_daily_breakdown(30)

    assert len(result) == 30
    assert result[0]["date"] == (today - timedelta(days=29)).isoformat()
    assert result[29]["date"] == today.isoformat()
    # Day with data should have values
    assert result[28]["on_time_pct"] == 100.0  # yesterday is index 28 (30-2)
    # Days without data have None
    assert result[0]["on_time_pct"] is None
```

- [ ] **Step 3: Run tests**

Run: `source .venv/bin/activate && pytest tests/ -v --tb=short`
Expected: 108 passed (92 existing + 16 new)

- [ ] **Step 4: Commit**

```bash
git add custom_components/cfl_commute/statistics.py tests/test_statistics.py
git commit -m "feat: add CFLCommuteStatisticsStore for persistent daily stats tracking"
```

---

### Task 3: Wire stats_store into coordinator

**Files:**
- Modify: `custom_components/cfl_commute/coordinator.py`

The coordinator needs a `stats_store` attribute (set to `None` externally by `__init__.py`, like upstream) and must call `async_record_observation` after a successful data fetch.

- [ ] **Step 1: Add import and stats_store attribute to coordinator**

Add `from typing import Any` after existing stdlib imports. The current imports start with:

```python
import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
```

Add:

```python
from typing import Any
```

In the existing `from .const import (...)` block, add:

```python
from .const import (
    # ... existing imports ...
    STATUS_CANCELLED,
    STATUS_DELAYED,
    STATUS_ON_TIME,
)
```

Add `stats_store` attribute in `__init__` after the threshold setup (before `super().__init__`):

```python
# Historical statistics store (set externally by async_setup_entry)
self.stats_store: Any | None = None
```

- [ ] **Step 2: Add stats recording in `_async_update_data`**

In `_async_update_data`, right after `self._failed_updates = 0` and before `return filtered_departures`, add:

```python
# Record observation in historical stats store
if self.stats_store is not None and filtered_departures:
    on_time_count = sum(
        1 for d in filtered_departures
        if not d.is_cancelled and d.delay_minutes == 0
    )
    delayed_count = sum(
        1 for d in filtered_departures
        if not d.is_cancelled and d.delay_minutes > 0
    )
    cancelled_count = sum(1 for d in filtered_departures if d.is_cancelled)
    services_tracked = len(filtered_departures)

    services = []
    for d in filtered_departures:
        if d.is_cancelled:
            status = STATUS_CANCELLED
        elif d.delay_minutes > 0:
            status = STATUS_DELAYED
        else:
            status = STATUS_ON_TIME
        services.append({
            "status": status,
            "delay_minutes": d.delay_minutes,
            "is_cancelled": d.is_cancelled,
        })

    await self.stats_store.async_record_observation({
        "on_time_count": on_time_count,
        "delayed_count": delayed_count,
        "cancelled_count": cancelled_count,
        "services_tracked": services_tracked,
        "services": services,
    })
```

- [ ] **Step 3: Run existing tests**

Run: `source .venv/bin/activate && pytest tests/ -v --tb=short`
Expected: 108 passed (no regression since coordinator tests use standalone functions, not the actual class)

- [ ] **Step 4: Commit**

```bash
git add custom_components/cfl_commute/coordinator.py
git commit -m "feat: wire stats_store into coordinator for observation recording"
```

---

### Task 4: Wire stats_store into __init__.py and create services.yaml

**Files:**
- Modify: `custom_components/cfl_commute/__init__.py`
- Create: `custom_components/cfl_commute/services.yaml`

- [ ] **Step 1: Create `custom_components/cfl_commute/services.yaml`**

```yaml
get_historical_raw_data:
  name: Get Historical Raw Data
  description: Retrieve the full raw historical daily statistics for a commute. Returns up to 90 days of per-day on-time and delay data.
  fields:
    entry_id:
      name: Entry ID
      description: The config entry ID of the commute (find it in Settings -> Integrations).
      required: true
      selector:
        text: {}
```

- [ ] **Step 2: Modify `__init__.py`**

Add new imports at the top:

```python
import voluptuous as vol
from homeassistant.core import ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
```

Update existing const import block to add:

```python
from .const import (
    CONF_NUM_TRAINS,
    DOMAIN,
    CONF_API_KEY,
    CONF_ORIGIN,
    CONF_DESTINATION,
    SERVICE_GET_HISTORICAL_RAW_DATA,
)
```

Add import for statistics:

```python
from .statistics import CFLCommuteStatisticsStore
```

In `async_setup_entry`, right after `coordinator = CFLCommuteDataUpdateCoordinator(...)` and before `await coordinator.async_config_entry_first_refresh()`, add:

```python
# Set up historical statistics store
stats_store = CFLCommuteStatisticsStore(hass, entry.entry_id)
await stats_store.async_load()
coordinator.stats_store = stats_store
```

After `entry.async_on_unload(entry.add_update_listener(async_reload_entry))` and before `return True`, add:

```python
# Register domain-wide service (only once across all entries)
if not hass.services.has_service(DOMAIN, SERVICE_GET_HISTORICAL_RAW_DATA):
    async def _handle_get_historical_raw_data(call: ServiceCall) -> dict:
        entry_id = call.data["entry_id"]
        if entry_id not in hass.data.get(DOMAIN, {}):
            raise ServiceValidationError(
                f"No commute found with entry_id: {entry_id}"
            )
        entry_data = hass.data[DOMAIN][entry_id]
        coordinator = entry_data["coordinator"]
        return {"days": coordinator.stats_store.get_raw_data()}

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_HISTORICAL_RAW_DATA,
        _handle_get_historical_raw_data,
        schema=vol.Schema({vol.Required("entry_id"): cv.string}),
        supports_response=SupportsResponse.ONLY,
    )
```

Update `async_unload_entry` to clean up the service when the last entry is unloaded:

```python
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    # Remove domain-wide service when the last entry is unloaded
    if unload_ok and not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_GET_HISTORICAL_RAW_DATA)

    return unload_ok
```

- [ ] **Step 3: Run tests**

Run: `source .venv/bin/activate && pytest tests/ -v --tb=short`
Expected: 108 passed

- [ ] **Step 4: Commit**

```bash
git add custom_components/cfl_commute/__init__.py custom_components/cfl_commute/services.yaml
git commit -m "feat: wire stats_store initialization and get_historical_raw_data service"
```

---

### Task 5: Add historical sensor entities

**Files:**
- Modify: `custom_components/cfl_commute/sensor.py`

Add two new sensor classes: `CFLCommuteHistoricalReliabilitySensor` and `CFLCommuteHistoricalDelaysSensor`. Register them in `async_setup_entry`.

- [ ] **Step 1: Add imports to sensor.py**

Add these to the existing imports from const:

```python
from .const import (
    ATTR_AVG_DELAY_7D,
    ATTR_AVG_DELAY_TODAY,
    ATTR_BEST_DAY,
    ATTR_CANCELLED_COUNT_TODAY,
    ATTR_DAILY_BREAKDOWN,
    ATTR_DELAYED_COUNT_TODAY,
    ATTR_ON_TIME_COUNT_TODAY,
    ATTR_ON_TIME_PCT_30D,
    ATTR_ON_TIME_PCT_7D,
    ATTR_ON_TIME_PCT_TODAY,
    ATTR_TOTAL_OBSERVATIONS_TODAY,
    ATTR_WORST_DAY,
)
```

- [ ] **Step 2: Add sensor classes to sensor.py (after CFLCommuteTrainSensor)**

```python
class CFLCommuteHistoricalReliabilitySensor(CoordinatorEntity, SensorEntity):
    """Sensor exposing on-time percentage over rolling windows."""

    def __init__(self, coordinator, commute_name):
        super().__init__(coordinator)
        self._commute_name = commute_name

    @property
    def name(self) -> str:
        return f"{self._commute_name} Historical Reliability"

    @property
    def unique_id(self) -> str:
        return f"{self._commute_name}_historical_reliability"

    @property
    def icon(self) -> str:
        return "mdi:chart-line"

    @property
    def unit_of_measurement(self) -> str:
        return "%"

    @property
    def state(self):
        if self.coordinator.stats_store is None:
            return None
        return self.coordinator.stats_store.get_rolling_stats(7)["on_time_pct"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        store = self.coordinator.stats_store
        if store is None:
            return {}

        today = store.get_today_stats()
        rolling_7 = store.get_rolling_stats(7)
        rolling_30 = store.get_rolling_stats(30)

        return {
            ATTR_ON_TIME_PCT_TODAY: today.get("on_time_pct"),
            ATTR_ON_TIME_PCT_7D: rolling_7["on_time_pct"],
            ATTR_ON_TIME_PCT_30D: rolling_30["on_time_pct"],
            ATTR_ON_TIME_COUNT_TODAY: today.get("on_time_count", 0),
            ATTR_DELAYED_COUNT_TODAY: today.get("delayed_count", 0),
            ATTR_CANCELLED_COUNT_TODAY: today.get("cancelled_count", 0),
            ATTR_TOTAL_OBSERVATIONS_TODAY: today.get("total_observations", 0),
            "days_with_data_7day": rolling_7["days_with_data"],
            "days_with_data_30day": rolling_30["days_with_data"],
            ATTR_DAILY_BREAKDOWN: store.get_daily_breakdown(30),
        }


class CFLCommuteHistoricalDelaysSensor(CoordinatorEntity, SensorEntity):
    """Sensor exposing average delay statistics over rolling windows."""

    def __init__(self, coordinator, commute_name):
        super().__init__(coordinator)
        self._commute_name = commute_name

    @property
    def name(self) -> str:
        return f"{self._commute_name} Historical Delays"

    @property
    def unique_id(self) -> str:
        return f"{self._commute_name}_historical_delays"

    @property
    def icon(self) -> str:
        return "mdi:clock-alert-outline"

    @property
    def unit_of_measurement(self) -> str:
        return "min"

    @property
    def state(self):
        if self.coordinator.stats_store is None:
            return None
        return self.coordinator.stats_store.get_rolling_stats(7)["avg_delay_minutes"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        store = self.coordinator.stats_store
        if store is None:
            return {}

        today = store.get_today_stats()
        rolling_7 = store.get_rolling_stats(7)
        best_worst = store.get_best_and_worst_days(30)

        return {
            ATTR_AVG_DELAY_TODAY: today.get("avg_delay_minutes"),
            ATTR_AVG_DELAY_7D: rolling_7["avg_delay_minutes"],
            ATTR_WORST_DAY: best_worst["worst_day"],
            ATTR_BEST_DAY: best_worst["best_day"],
            "days_with_data_7day": rolling_7["days_with_data"],
        }
```

- [ ] **Step 3: Register new sensors in `async_setup_entry`**

In `async_setup_entry`, after the loop that creates `CFLCommuteTrainSensor` instances and before `async_add_entities(sensors)`, add:

```python
    # Historical performance sensors
    sensors.append(
        CFLCommuteHistoricalReliabilitySensor(
            coordinator=coordinator, commute_name=commute_name
        )
    )
    sensors.append(
        CFLCommuteHistoricalDelaysSensor(
            coordinator=coordinator, commute_name=commute_name
        )
    )
```

- [ ] **Step 4: Run all tests**

Run: `source .venv/bin/activate && pytest tests/ -v --tb=short`
Expected: 108 passed (no existing tests for sensor entities)

- [ ] **Step 5: Commit**

```bash
git add custom_components/cfl_commute/sensor.py
git commit -m "feat: add HistoricalReliabilitySensor and HistoricalDelaysSensor entities"
```

---

### Task 6: Add historical + reverse-route stats to summary sensor

**Files:**
- Modify: `custom_components/cfl_commute/sensor.py`

Extend `CFLCommuteSummarySensor.extra_state_attributes` to include historical stats (from `self.coordinator.stats_store`) and reverse-route stats (from paired coordinator in `hass.data[DOMAIN]`).

- [ ] **Step 1: Add imports to sensor.py**

Add these to the const imports:

```python
from .const import (
    ATTR_AVG_DELAY_7D,
    ATTR_BEST_DAY,
    ATTR_REVERSE_AVG_DELAY_7D,
    ATTR_REVERSE_BEST_DAY,
    ATTR_REVERSE_ON_TIME_PCT_30D,
    ATTR_REVERSE_ON_TIME_PCT_7D,
    ATTR_REVERSE_ON_TIME_PCT_TODAY,
    ATTR_REVERSE_WORST_DAY,
    ATTR_ON_TIME_PCT_30D,
    ATTR_ON_TIME_PCT_7D,
    ATTR_ON_TIME_PCT_TODAY,
    ATTR_WORST_DAY,
    DOMAIN,
)
```

- [ ] **Step 2: Modify `CFLCommuteSummarySensor.extra_state_attributes`**

In the `extra_state_attributes` method, after the existing `attrs.update({...})` block and before `return attrs`, add:

```python
        # Include historical stats so the card can read them directly from this
        # entity without needing a separate lookup
        store = self.coordinator.stats_store
        if store is not None:
            today = store.get_today_stats()
            rolling_7 = store.get_rolling_stats(7)
            rolling_30 = store.get_rolling_stats(30)
            best_worst = store.get_best_and_worst_days(30)
            attrs[ATTR_ON_TIME_PCT_TODAY] = today.get("on_time_pct")
            attrs[ATTR_ON_TIME_PCT_7D] = rolling_7["on_time_pct"]
            attrs[ATTR_ON_TIME_PCT_30D] = rolling_30["on_time_pct"]
            attrs[ATTR_AVG_DELAY_7D] = rolling_7["avg_delay_minutes"]
            attrs[ATTR_WORST_DAY] = best_worst["worst_day"]
            attrs[ATTR_BEST_DAY] = best_worst["best_day"]

        # Expose the paired reverse route's stats so that a card configured with
        # only this entity still has access to both directions' stats when toggled.
        if self.hass is not None and DOMAIN in self.hass.data:
            rev_entry = next(
                (
                    entry_data
                    for entry_data in self.hass.data[DOMAIN].values()
                    if isinstance(entry_data, dict)
                    and entry_data.get("coordinator") is not None
                    and entry_data["coordinator"] is not self.coordinator
                    and entry_data["coordinator"].origin_id == self._destination_id
                    and entry_data["coordinator"].destination_id == self._origin_id
                ),
                None,
            )
            if rev_entry is not None:
                rev_coordinator = rev_entry["coordinator"]
                if rev_coordinator.stats_store is not None:
                    rev_store = rev_coordinator.stats_store
                    rev_today = rev_store.get_today_stats()
                    rev_7 = rev_store.get_rolling_stats(7)
                    rev_30 = rev_store.get_rolling_stats(30)
                    rev_bw = rev_store.get_best_and_worst_days(30)
                    attrs[ATTR_REVERSE_ON_TIME_PCT_TODAY] = rev_today.get("on_time_pct")
                    attrs[ATTR_REVERSE_ON_TIME_PCT_7D] = rev_7["on_time_pct"]
                    attrs[ATTR_REVERSE_ON_TIME_PCT_30D] = rev_30["on_time_pct"]
                    attrs[ATTR_REVERSE_AVG_DELAY_7D] = rev_7["avg_delay_minutes"]
                    attrs[ATTR_REVERSE_WORST_DAY] = rev_bw["worst_day"]
                    attrs[ATTR_REVERSE_BEST_DAY] = rev_bw["best_day"]

        return attrs
```

- [ ] **Step 3: Create `tests/test_sensor_historical.py` with non-regression tests**

```python
"""Tests for historical sensor entities and summary sensor historical stats."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.cfl_commute.const import (
    ATTR_AVG_DELAY_7D,
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

        # Original attrs still present
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
        rev_coordinator.origin_id = "200426001"  # Esch (swapped)
        rev_coordinator.destination_id = "200405060"  # Lux (swapped)
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

        # Forward stats unchanged
        assert attrs[ATTR_ON_TIME_PCT_TODAY] == 97.19
        assert attrs[ATTR_AVG_DELAY_7D] == 3.4

        # Reverse stats come from the reverse store
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

        # Place own coordinator in hass.data - the guard
        # `coordinator is not self.coordinator` must prevent matching
        own_coordinator.origin_id = "200426001"
        own_coordinator.destination_id = "200405060"
        sensor.hass.data[DOMAIN]["entry_self"] = {"coordinator": own_coordinator}

        attrs = sensor.extra_state_attributes

        assert ATTR_REVERSE_ON_TIME_PCT_TODAY not in attrs


# Non-regression: existing sensor interface unchanged
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
```

- [ ] **Step 4: Run all tests**

Run: `source .venv/bin/activate && pytest tests/ -v --tb=short`
Expected: 140 passed (92 existing + 16 stats_store + 32 historical sensor tests)

- [ ] **Step 5: Commit**

```bash
git add custom_components/cfl_commute/sensor.py tests/test_sensor_historical.py
git commit -m "feat: add historical and reverse-route stats to summary sensor attributes"
```

---

### Task 7: Final non-regression verification

- [ ] **Step 1: Run full test suite**

Run: `source .venv/bin/activate && pytest tests/ -v --tb=short`
Expected: 140 passed, 0 failed

- [ ] **Step 2: Run ruff linter**

Run: `source .venv/bin/activate && ruff check custom_components/ tests/`
Expected: No errors (or only pre-existing ones)

- [ ] **Step 3: Run black formatter check**

Run: `source .venv/bin/activate && black --check custom_components/ tests/`
Expected: Passes, or fix formatting

- [ ] **Step 4: Verify existing sensor behavior unchanged by running sensor tests specifically:**

Run: `source .venv/bin/activate && pytest tests/test_sensor.py tests/test_coordinator.py tests/test_api.py -v --tb=short`
Expected: All existing sensor/coordinator/api tests pass

---

## Self-Review Checklist

1. **Spec coverage:** All features from upstream V1.1.5 are covered:
   - [x] Historical performance tracking with persistent daily stats -> Task 2
   - [x] Daily breakdown attribute on historical sensor -> Task 5
   - [x] Get Historical Raw Data action -> Task 4
   - [x] Historical stats on CommuteSummarySensor -> Task 6
   - [x] Reverse route stats -> Task 6
   - [x] Drop daily_breakdown from Summary (16KB limit) -> Task 6

2. **Placeholder scan:** No TBD, TODOs, or placeholders in plan.

3. **Type consistency:** All method signatures, attribute names, and constants are consistent within the plan and match upstream patterns.

4. **Non-regression coverage:** All existing 92 tests pass unchanged. New tests verify backward compatibility of sensor state and attribute formats.

5. **No breaking changes:** Coordinator continues returning `list[Departure]`. Existing sensor class APIs unchanged. All existing unique_id patterns preserved.
