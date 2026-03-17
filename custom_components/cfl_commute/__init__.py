"""CFL Commute - Home Assistant integration for Luxembourg railways."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, CONF_API_KEY, CONF_ORIGIN, CONF_DESTINATION
from .api import CFLCommuteClient
from .coordinator import CFLCommuteDataUpdateCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CFL Commute from a config entry."""
    # Create API client
    api = CFLCommuteClient(entry.data[CONF_API_KEY])

    # Get station info
    origin = entry.data[CONF_ORIGIN]
    destination = entry.data[CONF_DESTINATION]

    # Create coordinator
    coordinator = CFLCommuteDataUpdateCoordinator(
        hass=hass,
        api=api,
        origin_id=origin["id"],
        origin_name=origin["name"],
        destination_id=destination["id"],
        destination_name=destination["name"],
        config=entry.data,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator and API in hass.data
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
        "config": entry.data,
    }

    # Forward to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
