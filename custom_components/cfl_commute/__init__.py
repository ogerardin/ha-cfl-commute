"""CFL Commute - Home Assistant integration for Luxembourg railways."""

import logging

import voluptuous as vol
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_NUM_TRAINS,
    DOMAIN,
    CONF_API_KEY,
    CONF_ORIGIN,
    CONF_DESTINATION,
    SERVICE_GET_HISTORICAL_RAW_DATA,
)
from .api import CFLCommuteClient
from .coordinator import CFLCommuteDataUpdateCoordinator
from .statistics import CFLCommuteStatisticsStore

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CFL Commute from a config entry."""
    # Use Home Assistant's managed session for proper lifecycle management
    session = async_get_clientsession(hass)
    api = CFLCommuteClient(entry.data[CONF_API_KEY], session=session)

    # Get station info
    origin = entry.data[CONF_ORIGIN]
    destination = entry.data.get(CONF_DESTINATION, {})

    # Create coordinator
    # Merge entry.data with entry.options (options override data)
    config = {**entry.data, **entry.options}
    coordinator = CFLCommuteDataUpdateCoordinator(
        hass=hass,
        api=api,
        origin_id=origin["id"],
        origin_name=origin["name"],
        destination_id=destination["id"],
        destination_name=destination["name"],
        config=config,
    )

    # Set up historical statistics store
    stats_store = CFLCommuteStatisticsStore(hass, entry.entry_id)
    await stats_store.async_load()
    coordinator.stats_store = stats_store

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator, API, and effective config (options override data) in hass.data
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
        "config": config,
    }

    # Forward to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for options changes
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

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

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    # Remove domain-wide service when the last entry is unloaded
    if unload_ok and not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_GET_HISTORICAL_RAW_DATA)

    return unload_ok


async def async_cleanup_stale_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove stale train entities when num_trains is reduced.

    Args:
        hass: Home Assistant instance
        entry: Config entry to clean up
    """
    new_num_trains = entry.options.get(
        CONF_NUM_TRAINS,
        entry.data.get(CONF_NUM_TRAINS, 3),
    )

    entity_reg = er.async_get(hass)

    entities_to_remove = []
    for entity in entity_reg.entities.values():
        if entity.config_entry_id != entry.entry_id:
            continue
        if not entity.entity_id.startswith("sensor."):
            continue
        if "_train_" not in entity.entity_id:
            continue

        entity_train_num = entity.entity_id.split("_train_")[-1]
        try:
            train_num = int(entity_train_num)
            if train_num > new_num_trains:
                entities_to_remove.append(entity.entity_id)
                _LOGGER.debug(
                    "Marking stale entity for removal: %s (train %d > %d)",
                    entity.entity_id,
                    train_num,
                    new_num_trains,
                )
        except ValueError:
            pass

    for entity_id in entities_to_remove:
        entity_reg.async_remove(entity_id)
        _LOGGER.info("Removed stale entity: %s", entity_id)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Reload a config entry with cleanup of stale entities.

    Args:
        hass: Home Assistant instance
        entry: Config entry to reload

    Returns:
        True if reload was successful
    """
    await async_cleanup_stale_entities(hass, entry)
    return await hass.config_entries.async_reload(entry.entry_id)
