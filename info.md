# CFL Commute

[![HACS-Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/ogerardin/hacs-cfl-commute.svg)](https://github.com/ogerardin/hacs-cfl-commute/releases)
[![License](https://img.shields.io/github/license/ogerardin/hacs-cfl-commute.svg)](LICENSE)

A custom Home Assistant integration that tracks regular commutes using CFL (Chemins de Fer Luxembourgeois) real-time data from the mobiliteit.lu API. Monitor train services, get disruption alerts, and automate your commuting routine.

## Features

- **Real-time Train Tracking**: Monitor upcoming train services between any two Luxembourg stations
- **Smart Update Intervals**: Automatically adjusts polling frequency based on time of day (peak/off-peak/night)
- **Disruption Detection**: Binary sensor that alerts on cancellations or significant delays
- **Rich Sensor Data**: Comprehensive attributes including platforms, delays, calling points, and more
- **Multi-Route Support**: Configure multiple commutes (e.g., morning and evening journeys)
- **UI Configuration**: Easy setup through Home Assistant's config flow interface
- **HACS Compatible**: Simple installation via Home Assistant Community Store

## Sensors

The integration creates multiple sensors for each configured commute:

### 1. Commute Summary Sensor

- **Entity ID**: `sensor.{commute_name}_summary`
- **State**: Summary of overall commute status (e.g., "3 trains on time", "2 trains delayed")
- **Attributes**:
  - Origin/destination names
  - Service counts (requested, tracked, total found)
  - On-time/delayed/cancelled counts
  - Time window setting
  - `all_trains`: Complete array of all tracked trains
  - Last updated and next update timestamps

### 2. Commute Status Sensor

- **Entity ID**: `sensor.{commute_name}_status`
- **State**: Overall commute status for easy automation triggers (hierarchical - highest severity wins)
  - `Normal` - All trains running on time (or below minor threshold)
  - `Minor Delays` - One or more trains delayed ≥ minor threshold (default 3 min, user-configurable)
  - `Major Delays` - One or more trains delayed ≥ major threshold (default 10 min, user-configurable)
  - `Severe Disruption` - One or more trains delayed ≥ severe threshold (default 15 min, user-configurable)
  - `Critical` - One or more trains cancelled (highest priority)
- **Icon**: Dynamic based on status
  - `mdi:train` - Normal
  - `mdi:train-variant` - Minor Delays
  - `mdi:clock-alert` - Major Delays
  - `mdi:alert-circle` - Severe Disruption
  - `mdi:alert-octagon` - Critical

### 3. Next Train Sensor

- **Entity ID**: `sensor.{commute_name}_next_train`
- **State**: Departure status (e.g., "On Time", "Delayed", "Cancelled", "Expected", "No service")
- **Icon**: Dynamic based on train status
- **Attributes**:
  - `train_number`: Always 1 (next train)
  - `departure_time`: Display departure time (HH:MM)
  - `scheduled_departure`: Original scheduled departure time
  - `expected_departure`: Expected departure time including delays
  - `platform`: Platform number or "TBA"
  - `platform_changed`: Boolean indicating if platform has changed
  - `operator`: Train operating company (CFL)
  - `delay_minutes`: Number of minutes delayed
  - `is_cancelled`: Boolean indicating cancellation
  - `calling_points`: List of stops the train will make

### 4. Individual Train Sensors

- **Entity IDs**: `sensor.{commute_name}_train_1`, `sensor.{commute_name}_train_2`, etc.
- **Count**: Created dynamically based on "Number of Services" configuration (1-10)
- **State**: Departure status (e.g., "On Time", "Delayed", "Cancelled")
- **Attributes**: Same as Next Train Sensor, with `train_number` indicating position

### 5. Has Disruption Binary Sensor

- **Entity ID**: `binary_sensor.{commute_name}_has_disruption`
- **State**: "on" when disruption detected, "off" when services are normal
- **Icon**: Dynamic based on disruption status
  - `mdi:alert-circle` - When on (disruption detected)
  - `mdi:check-circle` - When off (normal service)
- **Attributes**:
  - `current_status`: Current overall status
  - `cancelled_count`: Total count of cancelled trains
  - `delayed_count`: Total count of delayed trains
  - `max_delay_minutes`: Maximum delay in minutes
  - `disruption_reasons`: List of reasons for disruptions

## Prerequisites

### CFL API Key

You'll need a free API key by emailing: `opendata-api@atp.etat.lu`

## Installation

### HACS Installation (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add `https://github.com/ogerardin/hacs-cfl-commute` as repository
6. Select "Integration" as category
7. Click "Add"
8. Find "CFL Commute" in the integration list
9. Click "Download"
10. Restart Home Assistant

### Manual Installation

1. Download the latest release from [GitHub](https://github.com/ogerardin/hacs-cfl-commute/releases)
2. Extract the `custom_components/cfl_commute` directory
3. Copy it to your Home Assistant `custom_components` directory
4. Restart Home Assistant

## Configuration

### Initial Setup

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "CFL Commute"
4. Follow the configuration steps:

#### Step 1: API Authentication
- Enter your CFL API key
- The integration will validate your credentials

#### Step 2: Route Configuration
- **Origin Station**: Search for your origin station
- **Destination Station**: Search for your destination station

#### Step 3: Commute Settings
- **Commute Name**: Friendly name (default: "Origin to Destination")
- **Time Window**: How many minutes ahead to look (15-120 minutes, default: 60)
- **Number of Services**: How many trains to track (1-10, default: 3)
- **Severe Disruption Threshold**: Minutes of delay for "Severe Disruption" status (default: 15)
- **Major Delays Threshold**: Minutes of delay for "Major Delays" status (default: 10)
- **Minor Delays Threshold**: Minutes of delay for "Minor Delays" status (default: 3)
- **Enable Night-Time Updates**: Keep polling during night hours (23:00-05:00)

### Modifying Settings

1. Go to **Settings** → **Devices & Services**
2. Find your CFL Commute integration
3. Click **Configure**
4. Adjust your settings

### Multiple Commutes

To track multiple routes, add the integration multiple times with different origin/destination pairs.

## Update Intervals

The integration automatically adjusts update frequency based on time of day:

- **Peak Hours** (06:00-10:00, 16:00-20:00): Every 2 minutes
- **Off-Peak Hours**: Every 5 minutes
- **Night Time** (23:00-05:00): Every 15 minutes (or disabled if "Enable Night-Time Updates" is off)

## Automation Examples

### Simple Status Change Alert

```yaml
automation:
  - alias: "Alert on Commute Status Change"
    trigger:
      - platform: state
        entity_id: sensor.morning_commute_status
        to:
          - "Minor Delays"
          - "Major Delays"
          - "Severe Disruption"
          - "Critical"
    action:
      - service: notify.mobile_app
        data:
          title: "Commute Status: {{ states('sensor.morning_commute_status') }}"
          message: "Your commute has affected trains."
```

### Disruption Notification

```yaml
automation:
  - alias: "Alert on Commute Disruption"
    trigger:
      - platform: state
        entity_id: binary_sensor.morning_commute_has_disruption
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Commute Disruption!"
          data:
            priority: high
```

### Pre-Departure Reminder

```yaml
automation:
  - alias: "Next Train Departure Soon"
    trigger:
      - platform: template
        value_template: >
          {% set dep = state_attr('sensor.morning_commute_next_train', 'departure_time') %}
          {% if dep %}
            {% set dep_time = today_at(dep) %}
            {{ (dep_time - now()).total_seconds() / 60 < 10 and (dep_time - now()).total_seconds() > 0 }}
          {% else %}
            false
          {% endif %}
    action:
      - service: notify.mobile_app
        data:
          title: "Train Departing Soon"
          message: "Your train departs in 10 minutes from platform {{ state_attr('sensor.morning_commute_next_train', 'platform') }}"
```

## Troubleshooting

### Integration Not Showing Up

1. Ensure you've restarted Home Assistant after installation
2. Check the logs: **Settings** → **System** → **Logs**
3. Verify the `custom_components/cfl_commute` directory exists

### Authentication Errors

- Double-check your API key is correct
- Ensure you have a valid API key from opendata-api@atp.etat.lu

### No Data Showing

- Check if trains actually run on your route at this time
- Verify your time window is appropriate
- Review Home Assistant logs for API errors

### Sensors Not Updating

- Check your update interval settings
- If during night hours, ensure "Enable Night-Time Updates" is on
- Verify network connectivity

## API Information

This integration uses the [mobiliteit.lu HAFAS API](https://data.public.lu/en/datasets/api-mobiliteit-lu/). See [README.md](README.md) for details.

## Fork

This is a fork of [adamf83/my-rail-commute](https://github.com/adamf83/my-rail-commute) adapted for Luxembourg CFL trains instead of UK National Rail.

## Support

- **Issues**: [GitHub Issues](https://github.com/ogerardin/hacs-cfl-commute/issues)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Version**: 0.0.1
**Minimum Home Assistant Version**: 2024.1.0
