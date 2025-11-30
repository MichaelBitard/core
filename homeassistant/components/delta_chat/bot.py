"""Code related to the Delta Chat bot."""

import logging
from os import makedirs, path
from threading import Thread

from deltabot_cli.cli import ConfigProgressBar
from deltachat2 import Bot, CoreEvent, Event, EventType, IOTransport, JsonRpcError, Rpc
from deltachat2.events import HookCollection, RawEvent

from .const import DEFAULT_PATH

_LOGGER = logging.getLogger(__name__)


class DeltaBot:
    """Code related to the Delta Chat bot."""

    def __init__(self, relay: str, log_level: str = "info") -> None:
        """Bot constructor."""
        self.relay = relay
        self.log_level = log_level
        self._hooks = HookCollection()
        self._bot: Bot

    def get_accounts_dir(self) -> str:
        """Get bot's account folder."""
        if not path.exists(DEFAULT_PATH):
            makedirs(DEFAULT_PATH)
        return path.join(DEFAULT_PATH, "accounts")

    def is_ok(self) -> bool:
        """Placeholder for __init__ validation."""
        return True

    async def init(self) -> bool:
        """Initialize the bot."""
        accounts_dir = self.get_accounts_dir()

        with IOTransport(accounts_dir=accounts_dir) as trans:
            rpc = Rpc(trans)
            self._bot = Bot(rpc, self._hooks, _LOGGER)

            core_version = rpc.get_system_info().deltachat_core_version
            self._bot.logger.debug("Running deltachat core %s", core_version)
            return _init_cmd(self, self._bot, f"DCACCOUNT:https://{self.relay}/new")


def _init_cmd(_cli: DeltaBot, bot: Bot, full_relay: str) -> bool:
    """Initialize the account."""

    def process_events() -> None:
        events = (EventType.INFO, EventType.WARNING, EventType.ERROR)
        while True:
            raw_event = bot.rpc.get_next_event()
            accid = raw_event.context_id
            event = CoreEvent(raw_event.event)
            if event.kind == EventType.CONFIGURE_PROGRESS:
                if event.comment:
                    bot.logger.info(event.comment)
                pbar.set_progress(event.progress)
            elif event.kind in events:
                bot._on_event(Event(accid, event), RawEvent)  # noqa: SLF001
            if pbar.progress in (-1, pbar.total):
                break

    accid = bot.rpc.add_account()

    bot.logger.info("Starting configuration process...")
    bot.rpc.set_config(accid, "bot", "1")
    pbar = ConfigProgressBar()
    task = Thread(target=process_events, daemon=True)
    task.start()
    try:
        bot.rpc.add_transport_from_qr(accid, full_relay)
        task.join()
    except JsonRpcError as err:
        bot.logger.error(err)
        pbar.progress = -1
    pbar.close()
    if pbar.progress == -1:
        bot.logger.error("Configuration failed.")
    else:
        bot.logger.info("Account configured successfully.")

    return pbar.progress == pbar.total
