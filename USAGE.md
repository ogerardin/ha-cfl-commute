# CFL Commute

The integration is based on the notion of "commute". A commute is a single trip from an origin station to a destination station.
At the moment, a commute does not include itineraries that require a train change

## Configuration

### Initial Setup

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "CFL Commute"
4. Follow the configuration steps:

#### Step 1: API Key (skipped if already configured)
- Enter your CFL API key
- This step is skipped if you already have a commute configured
- The API key is shared across all commutes

#### Step 2: Origin Station
- Search for your origin station using the searchable dropdown
- Select your station from the results

#### Step 3: Destination Station
- Search for your destination station
- Select your station from the results

#### Step 4: Commute Settings
- **Commute Name**: Friendly name (default: "Origin → Destination")
- **Time Window (minutes)**: How many minutes ahead to look (0-180, default: 60, use 0 for all departures)
- **Number of Trains**: How many trains to track (1-10, default: 3)
- **Minor Delays Threshold (min)**: Minutes of delay for "Minor Delays" status (default: 3)
- **Major Delays Threshold (min)**: Minutes of delay for "Major Delays" status (default: 10)
- **Severe Disruption Threshold (min)**: Minutes of delay for "Severe Disruption" status (default: 15)
- **Enable Night Updates**: Keep polling during night hours (23:00-05:00)

#### Step 5: Return Journey (optional)
- Option to track the reverse commute automatically
- Skipped if the reverse commute is already configured

### Modifying Settings

1. Go to **Settings** → **Devices & Services**
2. Find your CFL Commute integration
3. Click **Configure**
4. Adjust your settings

### Multiple Commutes

To track additional commutes, click on "Add entry" and configure as many different origin/destination pairs as required.



## Sensor details
Each configured commute creates multiple sensors

### 1. Commute Summary Sensor

- **Entity ID**: `sensor.{commute_name}_summary`
- **State**: Summary of overall commute status (e.g., "3 trains on time", "2 trains delayed")
- **Attributes**:
  - `origin`/`destination`: Station names
  - `origin_id`/`destination_id`: Station IDs
  - `on_time_count`/`delayed_count`/`cancelled_count`: Train counts
  - `total_trains`: Total trains found
  - `all_trains`: Array of all tracked trains with number, times, platform, delay, cancelled status

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
- **State**: Departure status ("On Time", "Delayed", "Cancelled", or "No trains")
- **Icon**: Dynamic based on train status
- **Attributes**:
  - `train_number`: Train position (1 for next train)
  - `total_trains`: Total trains tracked
  - `departure_time`: Expected departure time (HH:MM)
  - `scheduled_departure`: Original scheduled departure time
  - `expected_departure`: Expected departure time including delays
  - `platform`: Platform number or "TBA"
  - `operator`: Train operating company (CFL)
  - `delay_minutes`: Minutes delayed
  - `is_cancelled`: Boolean indicating cancellation
  - `calling_points`: List of stops the train will make
  - `direction`: Train destination direction

### 4. Individual Train Sensors

- **Entity IDs**: `sensor.{commute_name}_train_1`, `sensor.{commute_name}_train_2`, etc.
- **Count**: Created dynamically based on "Number of Services" configuration (1-10)
- **State**: Departure status (e.g., "On Time", "Delayed", "Cancelled")
- **Attributes**: Same as Next Train Sensor

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

## Update Intervals

The integration automatically adjusts update frequency based on time of day:

- **Peak Hours** (06:00-10:00, 16:00-20:00): Every 2 minutes
- **Off-Peak Hours**: Every 5 minutes
- **Night Time** (23:00-05:00): Every 60 minutes (or every 15 minutes if "Enable Night-Time Updates" is on)

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
