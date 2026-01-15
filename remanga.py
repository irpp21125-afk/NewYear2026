from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import aiosqlite


@dataclass(frozen=True)
class Card:
    external_source: str
    external_id: str
    name: str


class CardProvider:
    """Abstraction for where 'cards' come from.

    We'll implement Remanga scraping once we know the page structure and what to treat as 'cards'.
    """

    async def fetch_cards(self, profile_url: str) -> Sequence[Card]:
        raise NotImplementedError


class RemangaPlaceholderProvider(CardProvider):
    async def fetch_cards(self, profile_url: str) -> Sequence[Card]:
        # TODO: implement after we have example profiles / DOM structure.
        return []


async def set_profile_url(conn: aiosqlite.Connection, discord_user_id: int, profile_url: str | None) -> None:
    await conn.execute(
        "INSERT OR IGNORE INTO users(discord_user_id) VALUES (?)",
        (discord_user_id,),
    )
    await conn.execute(
        "UPDATE users SET remanga_profile_url=? WHERE discord_user_id=?",
        (profile_url, discord_user_id),
    )


async def get_profile_url(conn: aiosqlite.Connection, discord_user_id: int) -> str | None:
    cur = await conn.execute(
        "SELECT remanga_profile_url FROM users WHERE discord_user_id=?",
        (discord_user_id,),
    )
    row = await cur.fetchone()
    return str(row[0]) if row and row[0] else None
