"""Constants for the Delta Chat integration."""

from dataclasses import dataclass
from typing import Final

DOMAIN: Final = "delta_chat"

CONF_DELTACHAT_RELAY: Final = "relay"
CONF_ADD_ANOTHER: Final = "add another"
DEFAULT_RELAY: Final = "nine.testrun.org"
DEFAULT_PATH: Final = "delta_chat"


@dataclass
class DeltaChatData:
    """DeltaChat runtime data."""

    relay: str
    users: list[tuple[str, str]]
