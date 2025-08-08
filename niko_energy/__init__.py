"""The Niko Energy Monitor integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the component."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up from a config entry."""
    #hass.async_create_task(
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    #)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    # Stop monitor
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        monitor = hass.data[DOMAIN][entry.entry_id]
        monitor.stop()
        del hass.data[DOMAIN][entry.entry_id]
    
    # Unload sensor platform
    return await hass.config_entries.async_forward_entry_unload(entry, "sensor")