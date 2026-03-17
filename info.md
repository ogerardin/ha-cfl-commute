# CFL Commute

A custom Home Assistant integration that tracks regular commutes using CFL (Chemins de Fer Luxembourgeois) real-time data from the mobiliteit.lu API. Monitor train services, get disruption alerts, and automate your commuting routine.

## Features

- **Real-time Train Tracking**: Monitor upcoming train services between any two Luxembourg stations
- **Smart Update Intervals**: Automatically adjusts polling frequency based on time of day (peak/off-peak/night)
- **Disruption Detection**: Binary sensor that alerts on cancellations or significant delays
- **Rich Sensor Data**: Comprehensive attributes including platforms, delays, calling points, and more
- **Multi-Route Support**: Configure multiple commutes (e.g., morning and evening journeys)
- **UI Configuration**: Easy setup through Home Assistant's config flow interface

## Sensors

The integration creates multiple sensors for each configured commute:

1. **Commute Summary Sensor** - Overview of all tracked services
2. **Commute Status Sensor** - Hierarchical status (Normal → Critical)
3. **Next Train Sensor** - Detailed information about the next departure
4. **Individual Train Sensors** - Track multiple upcoming trains
5. **Has Disruption Binary Sensor** - Alerts when disruption is detected

## Prerequisites

### CFL API Key

You'll need a free API key from opendata-api@atp.etat.lu

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "CFL Commute"
4. Follow the configuration steps:
   - Enter your CFL API key
   - Search for origin and destination stations
   - Configure commute settings (name, time window, number of services)

## Update Intervals

The integration automatically adjusts update frequency:

- **Peak Hours** (06:00-10:00, 16:00-20:00): Every 2 minutes
- **Off-Peak Hours**: Every 5 minutes
- **Night Time** (23:00-05:00): Every 15 minutes (or disabled if night-time updates are off)

## Fork

This is a fork of [adamf83/my-rail-commute](https://github.com/adamf83/my-rail-commute) adapted for Luxembourg CFL trains instead of UK National Rail.

## Support

For issues, questions, or feature requests, please visit the [GitHub repository](https://github.com/ogerardin/hacs-cfl-commute).
