[![HACS-Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/ogerardin/ha-cfl-commute.svg)](https://github.com/ogerardin/ha-cfl-commute/releases)
[![License](https://img.shields.io/github/license/ogerardin/ha-cfl-commute.svg)](LICENSE)

# CFL Commute
This is a Home Assistant integration for tracking Luxembourg CFL train commutes. 
Monitor trains, get disruption alerts, and automate your commuting routine. 

## Features
- **Real-time Train Tracking**: Monitor upcoming trains between any two Luxembourg stations
- **Smart Update Intervals**: Automatically adjusts polling frequency based on time of day (peak/off-peak/night)
- **Disruption Detection**: Binary sensor that alerts on cancellations or significant delays
- **Rich Sensor Data**: Comprehensive attributes including platforms, delays, calling points, and more
- **Multi-Route Support**: Configure multiple commutes (e.g., morning and evening journeys)
- **UI Configuration**: Easy setup through Home Assistant's config flow interface
- **HACS Compatible**: Simple installation via Home Assistant Community Store

## Requirements
- A working installation of [Home Assistant](https://www.home-assistant.io/)
- An API key for the mobiliteit.lu API. Request your API key by emailing: [opendata-api@atp.etat.lu](mailto:opendata-api@atp.etat.lu)
- (optional, recommended for easy installation): [HACS](https://www.hacs.xyz/docs/use/)

## Installation
Choose one of the following methods (easiest first).

### Using HACS (easy method)
1. Follow this link:   
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ogerardin&repository=ha-cfl-commute&category=integration)
2. Confirm adding custom repository
3. Click on "Download" button (bottom right) and confirm
4. When it's downloaded, you will have a notification in "Settings" that tells you to restart HA. Accept the suggestion and let HA restart


### Using HACS (manually adding custom repo)

1. Open HACS
2. Click on "⋮" (top right), then "Custom repositories"
3. Fill in as follows:
   - Repository: `https://github.com/ogerardin/ha-cfl-commute`
   - Type: 'Integration'
4. Click "ADD"; after a few seconds the new integration appears under the "New" heading
5. Click on "⋮" on the corresponding row, then "Download" and confirm
6. When it's downloaded, you will have a notification in "Settings" that tells you to restart HA. Accept the suggestion and let HA restart

### Manual installation
1. Copy `custom_components/cfl_commute` to `config/custom_components/`
2. Restart HA

## What next?
- Check the user guide: [USAGE.md](USAGE.md)
- for a richer visual experience, install the companion [CFL Commute Card](https://github.com/ogerardin/lovelace-cfl-commute-card)

## Support
- Issues: [GitHub issues](https://github.com/ogerardin/ha-cfl-commute/issues)

## Acknowledgments
This integration was forked from [adamf83/my-rail-commute](https://github.com/adamf83/my-rail-commute) (UK National Rail), thanks to the author for inspiration.

Real time data is obtained from mobiliteit.lu HAFAS OpenData API:
- **Provider**: CFL (Chemins de Fer Luxembourgeois)
- **API**: [mobiliteit.lu HAFAS API](https://data.public.lu/en/datasets/api-mobiliteit-lu/)

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer
This is an unofficial integration and is not affiliated with, endorsed by, or connected to CFL (Chemins de Fer Luxembourgeois) or mobiliteit.lu. Use at your own risk.

Train times and information are provided by the mobiliteit.lu HAFAS API. While we strive for accuracy, always verify critical journey information through official channels.
