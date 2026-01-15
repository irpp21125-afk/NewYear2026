from __future__ import annotations

# pyright: reportUnusedFunction=false

import sys
from datetime import timedelta
from pathlib import Path

import discord
from discord import app_commands

# Allow running as a file: `python bot/main.py`.
# (Preferred is `python -m bot.main` from project root.)
if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from bot.config import load_settings
from bot.db import Db, get_balance, is_game_banned
from bot import economy as economy_mod
from bot import games as games_mod
from bot import remanga as remanga_mod
from bot import moderation as moderation_mod


class BotApp(discord.Client):
    def __init__(self, db: Db):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.db = db

    async def setup_hook(self) -> None:
        # Global sync is ok for MVP; later you can scope by guild for faster iteration.
        await self.tree.sync()


def build_rules_text() -> str:
    # MVP rules; we'll refine with your requirements.
    return (
        "**Правила игр (черновик):**\n"
        "1) Нельзя обманывать с ставками/результатами.\n"
        "2) Нельзя спамить вызовами/играми.\n"
        "3) Любая ставка фиксируется ботом. Споры решают модераторы/админы.\n"
        "4) За нарушение: бан от игр (временный или перманент).\n"
    )


async def main_async() -> None:
    settings = load_settings()
    db = Db(settings.database_path)
    await db.init()

    client = BotApp(db=db)

    @client.tree.command(name="rules", description="Показать правила игр")
    async def rules(interaction: discord.Interaction):
        await interaction.response.send_message(build_rules_text(), ephemeral=True)

    @client.tree.command(name="balance", description="Показать баланс")
    async def balance(interaction: discord.Interaction, user: discord.User | None = None):
        target = user or interaction.user
        async with await db.connect() as conn:
            bal = await get_balance(conn, target.id)
            await conn.commit()
        await interaction.response.send_message(f"Баланс {target.mention}: {bal}")

    @client.tree.command(name="daily", description="Получить ежедневную награду")
    async def daily(interaction: discord.Interaction):
        async with await db.connect() as conn:
            banned, reason = await is_game_banned(conn, interaction.user.id)
            if banned:
                await interaction.response.send_message(f"Ты забанен от игр. Причина: {reason or '—'}", ephemeral=True)
                return

            ok, bal, msg = await economy_mod.claim_daily(conn, interaction.user.id)
            await conn.commit()

        await interaction.response.send_message(f"{msg} Текущий баланс: {bal}", ephemeral=not ok)

    @client.tree.command(name="coinflip", description="Монетка на деньги: 50/50")
    async def coinflip(interaction: discord.Interaction, amount: int):
        async with await db.connect() as conn:
            banned, reason = await is_game_banned(conn, interaction.user.id)
            if banned:
                await interaction.response.send_message(f"Ты забанен от игр. Причина: {reason or '—'}", ephemeral=True)
                return

            ok, bal, msg = await games_mod.coinflip(conn, interaction.user.id, amount)
            await conn.commit()

        await interaction.response.send_message(f"{msg} Баланс: {bal}", ephemeral=not ok)

    @client.tree.command(name="set_remanga", description="Привязать remanga профиль URL")
    async def set_remanga(interaction: discord.Interaction, profile_url: str):
        async with await db.connect() as conn:
            await remanga_mod.set_profile_url(conn, interaction.user.id, profile_url)
            await conn.commit()
        await interaction.response.send_message("Ок, профиль сохранён. Автопроверка карт будет добавлена после уточнения формата.", ephemeral=True)

    @client.tree.command(name="mod_ban_games", description="(MOD) Забанить игрока от игр")
    async def mod_ban_games(interaction: discord.Interaction, user: discord.User, days: int = 7, reason: str | None = None):
        if not (moderation_mod.is_server_owner(interaction) or moderation_mod.has_moderation(interaction)):
            await interaction.response.send_message("Недостаточно прав.", ephemeral=True)
            return

        banned_until = None
        if days > 0:
            dt = discord.utils.utcnow() + timedelta(days=days)
            banned_until = dt.replace(tzinfo=None, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")

        async with await db.connect() as conn:
            from bot.db import set_game_ban

            await set_game_ban(conn, user.id, banned_until=banned_until, reason=reason)
            await conn.commit()

        await interaction.response.send_message(f"Ок. {user.mention} забанен от игр на {days} дн. Причина: {reason or '—'}")

    await client.start(settings.discord_token)


def main() -> None:
    import asyncio

    asyncio.run(main_async())


if __name__ == "__main__":
    main()
