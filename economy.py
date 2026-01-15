from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import aiosqlite

from bot import db as dbmod


DAILY_COOLDOWN_HOURS = 24
DAILY_REWARD = 100


async def claim_daily(conn: aiosqlite.Connection, user_id: int) -> tuple[bool, int, str]:
    """Returns (ok, new_balance, message)."""
    await dbmod.ensure_user(conn, user_id)

    cur = await conn.execute(
        "SELECT created_at FROM economy_logs WHERE discord_user_id=? AND action='daily' ORDER BY id DESC LIMIT 1",
        (user_id,),
    )
    row = await cur.fetchone()
    if row:
        # SQLite datetime('now') returns 'YYYY-MM-DD HH:MM:SS' (UTC)
        last = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if now - last < timedelta(hours=DAILY_COOLDOWN_HOURS):
            remaining = timedelta(hours=DAILY_COOLDOWN_HOURS) - (now - last)
            hours = int(remaining.total_seconds() // 3600)
            mins = int((remaining.total_seconds() % 3600) // 60)
            bal = await dbmod.get_balance(conn, user_id)
            return False, bal, f"Ещё рано. Попробуй через ~{hours}ч {mins}м."

    new_balance = await dbmod.add_balance(conn, user_id, DAILY_REWARD, action="daily", meta_json=json.dumps({"reward": DAILY_REWARD}))
    return True, new_balance, f"Ежедневная награда: +{DAILY_REWARD}."  # noqa: RUF001
