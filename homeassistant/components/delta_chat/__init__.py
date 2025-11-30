"""The Delta Chat integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .bot import _LOGGER, DeltaBot
from .const import CONF_DELTACHAT_RELAY, DeltaChatData

_PLATFORMS: list[Platform] = [Platform.NOTIFY]

type DeltaChatConfigEntry = ConfigEntry[DeltaChatData]


async def async_setup_entry(hass: HomeAssistant, entry: DeltaChatConfigEntry) -> bool:
    """Set up Delta Chat from a config entry."""

    conf = DeltaChatData(entry.data[CONF_DELTACHAT_RELAY])

    entry.runtime_data = conf

    try:
        client = DeltaBot(conf.relay)
        client.is_ok()
        _LOGGER.info("SETUP OK")
    except Exception as ex:
        raise ConfigEntryNotReady("Something went wrong") from ex

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: DeltaChatConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
