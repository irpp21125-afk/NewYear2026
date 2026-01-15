from __future__ import annotations

import random

import aiosqlite

from bot import db as dbmod


async def coinflip(conn: aiosqlite.Connection, user_id: int, stake: int) -> tuple[bool, int, str]:
    """Simple coinflip: 50/50.

    Returns (ok, new_balance, message).
    """
    if stake <= 0:
        bal = await dbmod.get_balance(conn, user_id)
        return False, bal, "Ставка должна быть > 0."

    current = await dbmod.get_balance(conn, user_id)
    if current < stake:
        return False, current, "Недостаточно средств."

    win = random.random() < 0.5
    delta = stake if win else -stake
    new_balance = await dbmod.add_balance(conn, user_id, delta, action="coinflip")

    if win:
        return True, new_balance, f"Монетка: победа. +{stake}."
    return True, new_balance, f"Монетка: поражение. -{stake}."
