# CFL Commute

This is a Home Assistant integration for tracking Luxembourg CFL train commutes.
It was forked from [adamf83/my-rail-commute](https://github.com/adamf83/my-rail-commute) (UK National Rail).

## Features

- **Real-time Train Tracking**: Monitor upcoming train services between any two Luxembourg stations
- **Smart Update Intervals**: Automatically adjusts polling frequency based on time of day (peak/off-peak/night)
- **Disruption Detection**: Binary sensor that alerts on cancellations or significant delays
- **Rich Sensor Data**: Comprehensive attributes including platforms, delays, calling points, and more
- **Multi-Route Support**: Configure multiple commutes (e.g., morning and evening journeys)
- **UI Configuration**: Easy setup through Home Assistant's config flow interface
- **HACS Compatible**: Simple installation via Home Assistant Community Store

## Requirements

A working installation of [Home Assistant](https://www.home-assistant.io/)

You will also need an API key for the mobiliteit.lu API.
Request your API key by emailing: [opendata-api@atp.etat.lu](mailto:opendata-api@atp.etat.lu)

## Installation

### Using HACS (recommended)
Requirement: [HACS](https://www.hacs.xyz/docs/use/) installed in your Home Assistant

1. Open HACS → Explore → Add Repository
2. Search for "CFL Commute" or add: `https://github.com/ogerardin/ha-cfl-commute`
3. Select "Integration"
4. Restart Home Assistant

### Manual installation
Copy `custom_components/cfl_commute` to `config/custom_components/`

## API
This integration uses the mobiliteit.lu HAFAS OpenData API:

- **Provider**: CFL (Chemins de Fer Luxembourgeois)
- **API**: [mobiliteit.lu HAFAS API](https://data.public.lu/en/datasets/api-mobiliteit-lu/)

## Documentation
Full user guide: [USAGE.md](USAGE.md)

## Support
[Issues](https://github.com/ogerardin/ha-cfl-commute/issues)
## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This is an unofficial integration and is not affiliated with, endorsed by, or connected to CFL (Chemins de Fer Luxembourgeois) or mobiliteit.lu. Use at your own risk.

Train times and information are provided by the mobiliteit.lu HAFAS API. While we strive for accuracy, always verify critical journey information through official channels.
