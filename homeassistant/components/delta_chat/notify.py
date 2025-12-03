"""DeltaChat for notify component."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.components.notify import NotifyEntity
from homeassistant.const import CONF_EMAIL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DeltaChatConfigEntry
from .bot import DeltaBot
from .const import CONF_DELTACHAT_RELAY

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA_MODERN = vol.Schema({})
DISCOVERY_SCHEMA = PLATFORM_SCHEMA_MODERN.extend({}, extra=vol.REMOVE_EXTRA)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DeltaChatConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up DeltaChat notify."""

    _LOGGER.info("Config %s", config_entry)
    _LOGGER.info("Config data %s", config_entry.data)
    async_add_entities(
        DeltaChatNotify(config_entry, entry["email"], entry["name"])
        for entry in config_entry.data[CONF_EMAIL]
    )


class DeltaChatNotify(NotifyEntity):
    """Representation of a notification entity service that can send messages using DeltaChat."""

    def __init__(self, config: DeltaChatConfigEntry, email: str, nom: str) -> None:
        """Initialize a DeltaChat notification."""
        _LOGGER.info("Init Notify %s %s", email, nom)
        self._attr_unique_id = nom
        self.contact = email
        self.bot = DeltaBot(config.data[CONF_DELTACHAT_RELAY])

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Send a message."""
        _LOGGER.info("Send message %s", message)
        await self.bot.send_message(message, self.contact)
