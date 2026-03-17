# CFL Commute

This is a Home Assistant integration for tracking Luxembourg CFL train commutes.
It was forked from [adamf83/my-rail-commute](https://github.com/adamf83/my-rail-commute) (UK National Rail).

## Requirements
A working installation of [Home Assistant](https://www.home-assistant.io/)

You will also need an API key for the mobiliteit.lu API.
Request your API key by emailing: [opendata-api@atp.etat.lu](mailto:opendata-api@atp.etat.lu)

## Installation
### Using HACS (recommended)
Requirement: [HACS](https://www.hacs.xyz/docs/use/) installed in your Home Assistant

1. Open HACS → Explore → Add Repository
2. Search for "CFL Commute" or add: `https://github.com/ogerardin/hacs-cfl-commute`
3. Select "Integration"
4. Restart Home Assistant

### Manual installation
Copy `custom_components/cfl_commute` to `config/custom_components/`

## API

This integration uses the mobiliteit.lu HAFAS OpenData API:

- **Provider**: CFL (Chemins de Fer Luxembourgeois)
- **API**: [mobiliteit.lu HAFAS API](https://data.public.lu/en/datasets/api-mobiliteit-lu/)
- **Base URL**: `https://cdt.hafas.de/opendata/apiserver`
- **Format**: REST/JSON

## Documentation
Full user guide: [info.md](info.md)

## Support
[Issues](https://github.com/ogerardin/hacs-cfl-commute/issues)
