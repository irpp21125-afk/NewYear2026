from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
import aiosqlite

# Allow running as a file: `python bot/db.py`.
# (Preferred is `python -m bot.db` from project root.)
if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))


SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS users (
  discord_user_id INTEGER PRIMARY KEY,
  remanga_profile_url TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS balances (
  discord_user_id INTEGER PRIMARY KEY,
  balance INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (discord_user_id) REFERENCES users(discord_user_id)
);

CREATE TABLE IF NOT EXISTS game_bans (
  discord_user_id INTEGER PRIMARY KEY,
  banned_until TEXT,
  reason TEXT,
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (discord_user_id) REFERENCES users(discord_user_id)
);

CREATE TABLE IF NOT EXISTS economy_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  discord_user_id INTEGER,
  action TEXT NOT NULL,
  amount INTEGER,
  meta_json TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_discord_user_id INTEGER NOT NULL,
  external_source TEXT,
  external_id TEXT,
  name TEXT NOT NULL,
  verified INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (owner_discord_user_id) REFERENCES users(discord_user_id)
);

CREATE INDEX IF NOT EXISTS idx_cards_owner ON cards(owner_discord_user_id);
"""


@dataclass
class Db:
    path: Path

    async def connect(self) -> aiosqlite.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = await aiosqlite.connect(str(self.path))
        await conn.execute("PRAGMA foreign_keys=ON;")
        await conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    async def init(self) -> None:
        async with await self.connect() as conn:
            await conn.executescript(SCHEMA_SQL)
            await conn.commit()


async def ensure_user(conn: aiosqlite.Connection, discord_user_id: int) -> None:
    await conn.execute(
        "INSERT OR IGNORE INTO users(discord_user_id) VALUES (?)",
        (discord_user_id,),
    )
    await conn.execute(
        "INSERT OR IGNORE INTO balances(discord_user_id, balance) VALUES (?, 0)",
        (discord_user_id,),
    )


async def get_balance(conn: aiosqlite.Connection, discord_user_id: int) -> int:
    await ensure_user(conn, discord_user_id)
    cur = await conn.execute(
        "SELECT balance FROM balances WHERE discord_user_id = ?",
        (discord_user_id,),
    )
    row = await cur.fetchone()
    return int(row[0]) if row else 0


async def add_balance(conn: aiosqlite.Connection, discord_user_id: int, delta: int, action: str, meta_json: str | None = None) -> int:
    await ensure_user(conn, discord_user_id)
    await conn.execute(
        "UPDATE balances SET balance = balance + ?, updated_at = datetime('now') WHERE discord_user_id = ?",
        (delta, discord_user_id),
    )
    await conn.execute(
        "INSERT INTO economy_logs(discord_user_id, action, amount, meta_json) VALUES (?, ?, ?, ?)",
        (discord_user_id, action, delta, meta_json),
    )
    cur = await conn.execute(
        "SELECT balance FROM balances WHERE discord_user_id = ?",
        (discord_user_id,),
    )
    row = await cur.fetchone()
    return int(row[0]) if row else 0


async def is_game_banned(conn: aiosqlite.Connection, discord_user_id: int) -> tuple[bool, str | None]:
    await ensure_user(conn, discord_user_id)
    cur = await conn.execute(
        "SELECT banned_until, reason FROM game_bans WHERE discord_user_id = ?",
        (discord_user_id,),
    )
    row = await cur.fetchone()
    if not row:
        return False, None

    banned_until, reason = row[0], row[1]
    if banned_until is None:
        return False, reason

    cur2 = await conn.execute("SELECT datetime('now') < datetime(?)", (banned_until,))
    row2 = await cur2.fetchone()
    active = bool(row2[0]) if row2 else False
    return active, reason


async def set_game_ban(conn: aiosqlite.Connection, discord_user_id: int, banned_until: str | None, reason: str | None) -> None:
    await ensure_user(conn, discord_user_id)
    await conn.execute(
        "INSERT INTO game_bans(discord_user_id, banned_until, reason) VALUES (?, ?, ?) "
        "ON CONFLICT(discord_user_id) DO UPDATE SET banned_until=excluded.banned_until, reason=excluded.reason, updated_at=datetime('now')",
        (discord_user_id, banned_until, reason),
    )


def main() -> None:
    from bot.config import load_settings

    settings = load_settings()
    db = Db(settings.database_path)

    asyncio.run(db.init())
    print(f"DB initialized at: {db.path}")


if __name__ == "__main__":
    main()
