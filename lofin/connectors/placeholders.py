from __future__ import annotations


class OptionalConnector:
    """Base placeholder for opt-in Discord, Telegram, and X/Twitter scrapers."""

    name = "optional"

    async def fetch(self) -> list[dict[str, object]]:
        return []


class DiscordConnector(OptionalConnector):
    name = "discord"


class TelegramConnector(OptionalConnector):
    name = "telegram"


class XTwitterConnector(OptionalConnector):
    name = "x_twitter"
