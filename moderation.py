from __future__ import annotations

import discord


def is_server_owner(interaction: discord.Interaction) -> bool:
    if not interaction.guild:
        return False
    return interaction.guild.owner_id == interaction.user.id


def has_admin(interaction: discord.Interaction) -> bool:
    if not interaction.guild:
        return False
    member = interaction.guild.get_member(interaction.user.id)
    if not member:
        return False
    perms = member.guild_permissions
    return bool(perms.administrator)


def has_moderation(interaction: discord.Interaction) -> bool:
    if not interaction.guild:
        return False
    member = interaction.guild.get_member(interaction.user.id)
    if not member:
        return False
    perms = member.guild_permissions
    return bool(perms.manage_guild or perms.manage_messages or perms.moderate_members or perms.administrator)
