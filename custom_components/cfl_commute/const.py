"""Constants for CFL Commute integration."""

from homeassistant.const import Platform

DOMAIN = "cfl_commute"

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

DEFAULT_TIME_WINDOW = 60
DEFAULT_NUM_TRAINS = 3
DEFAULT_MINOR_THRESHOLD = 3
DEFAULT_MAJOR_THRESHOLD = 10
DEFAULT_SEVERE_THRESHOLD = 15
DEFAULT_NIGHT_UPDATES = False

CONF_API_KEY = "api_key"
CONF_ORIGIN = "origin"
CONF_DESTINATION = "destination"
CONF_COMMUTE_NAME = "commute_name"
CONF_TIME_WINDOW = "time_window"
CONF_NUM_TRAINS = "num_trains"
CONF_MINOR_THRESHOLD = "minor_threshold"
CONF_MAJOR_THRESHOLD = "major_threshold"
CONF_SEVERE_THRESHOLD = "severe_threshold"
CONF_NIGHT_UPDATES = "night_updates"
CONF_ADD_RETURN_JOURNEY = "add_return_journey"
CONF_DEPARTED_TRAIN_GRACE_PERIOD = "departed_train_grace_period"

DEFAULT_DEPARTED_TRAIN_GRACE_PERIOD = 2  # minutes
MIN_GRACE_PERIOD = 0  # minutes
MAX_GRACE_PERIOD = 15  # minutes

STATUS_NORMAL = "Normal"
STATUS_MINOR = "Minor Delays"
STATUS_MAJOR = "Major Delays"
STATUS_SEVERE = "Severe Disruption"
STATUS_CRITICAL = "Critical"

TRAIN_ON_TIME = "On Time"
TRAIN_DELAYED = "Delayed"
TRAIN_CANCELLED = "Cancelled"
TRAIN_EXPECTED = "Expected"
TRAIN_NO_TRAIN = "No trains"

STATUS_ON_TIME = "on_time"
STATUS_DELAYED = "delayed"
STATUS_CANCELLED = "cancelled"

STORAGE_VERSION = 1
STATS_RETENTION_DAYS = 90

UPDATE_INTERVAL_PEAK = 120
UPDATE_INTERVAL_OFFPEAK = 300
UPDATE_INTERVAL_NIGHT = 900

# Smart interval configuration
PEAK_HOURS = [(6, 10), (16, 20)]  # 6-10am, 4-8pm
NIGHT_HOURS = (23, 5)  # 11pm-5am

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

ATTR_REVERSE_ON_TIME_PCT_TODAY = "reverse_on_time_pct_today"
ATTR_REVERSE_ON_TIME_PCT_7D = "reverse_on_time_pct_7day"
ATTR_REVERSE_ON_TIME_PCT_30D = "reverse_on_time_pct_30day"
ATTR_REVERSE_AVG_DELAY_7D = "reverse_avg_delay_7day"
ATTR_REVERSE_WORST_DAY = "reverse_worst_day"
ATTR_REVERSE_BEST_DAY = "reverse_best_day"

SERVICE_GET_HISTORICAL_RAW_DATA = "get_historical_raw_data"
