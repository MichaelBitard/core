"""Code related to the Delta Chat bot."""

import logging
from os import makedirs, path
from threading import Thread
import time
from typing import Final

from deltabot_cli.cli import BotCli, ConfigProgressBar
from deltachat2 import (
    Bot,
    CoreEvent,
    Event,
    EventType,
    IOTransport,
    JsonRpcError,
    MsgData,
    Rpc,
)
from deltachat2.events import HookCollection, RawEvent

from homeassistant.exceptions import HomeAssistantError

from .const import DEFAULT_PATH

_LOGGER = logging.getLogger(__name__)


DC_STR_CONTACT_VERIFIED: Final = 35


class DeltaBot:
    """Code related to the Delta Chat bot."""

    def __init__(self, relay: str, log_level: str = "info") -> None:
        """Bot constructor."""
        self.relay = relay
        self.log_level = log_level
        self._hooks = HookCollection()

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
            bot = Bot(rpc, self._hooks, _LOGGER)

            core_version = rpc.get_system_info().deltachat_core_version
            bot.logger.debug("Running deltachat core %s", core_version)
            return _init_cmd(self, bot, f"DCACCOUNT:https://{self.relay}/new")

    async def start(self) -> None:
        """Listen for incoming messages."""
        accounts_dir = self.get_accounts_dir()
        with IOTransport(accounts_dir=accounts_dir) as trans:
            rpc = Rpc(trans)
            bot = Bot(rpc, self._hooks, _LOGGER)
            return _serve_cmd(self, bot)

    async def send_message(self, message: str, target: str) -> None:
        """Send a message."""
        accounts_dir = self.get_accounts_dir()
        with IOTransport(accounts_dir=accounts_dir) as trans:
            rpc = Rpc(trans)
            bot = Bot(rpc, self._hooks, _LOGGER)

            core_version = rpc.get_system_info().deltachat_core_version
            bot.logger.debug("Running deltachat core %s", core_version)
            accid = bot.rpc.get_all_account_ids()[0]

            # first fetch incoming messages to have updated chats state
            bot.logger.info("first syncing chats state...")
            bot.rpc.accounts_background_fetch(60)

            bot.logger.info("sending message...")

            qrdata = bot.rpc.get_chat_securejoin_qr_code(accid, None)
            contacts = bot.rpc.get_contacts(accid, DC_STR_CONTACT_VERIFIED, "")

            _LOGGER.info("QRDATA %s", qrdata)
            _LOGGER.info("CONTACTS %s", contacts)
            chat_id = bot.rpc.create_chat_by_contact_id(
                # chat_id = bot.rpc.get_chat_id_by_contact_id(
                accid,
                11,
            )  # 11 = Take from contacts
            _LOGGER.info("CHAT_ID %s", chat_id)

            msgid = bot.rpc.send_msg(accid, chat_id, MsgData(text=message))
            bot.run_until(
                lambda ev: ev.event.kind
                in (EventType.MSG_DELIVERED, EventType.MSG_FAILED)
                and ev.event.msg_id == msgid
            )
            bot.logger.info("Done, message sent")


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


def _serve_cmd(cli: BotCli, bot: Bot) -> None:
    """Start processing messages."""
    rpc = bot.rpc
    accounts = rpc.get_all_account_ids()
    addrs = []
    for accid in accounts:
        addrs2 = _get_addresses(bot.rpc, accid)
        if addrs2:
            addrs.extend(addrs2)
        else:
            bot.logger.error("account %s not configured", accid)
    if len(addrs) != 0:
        bot.logger.info("Listening at: %s", f"{', '.join(addrs)}")
        # cli._on_start(bot, {})
        while True:
            try:
                bot.run_forever(0)
            except KeyboardInterrupt:
                return
            except Exception as ex:  # pylint:disable=broad-except
                bot.logger.exception(ex)  # noqa: TRY401
                time.sleep(5)
    else:
        bot.logger.error("There are no configured accounts to serve")
        raise NoAccount


def _get_addresses(rpc: Rpc, accid: int) -> list[str]:
    transports = rpc.list_transports(accid)
    return [params["addr"] for params in transports]


class NoAccount(HomeAssistantError):
    """Error to indicate there is no account."""
