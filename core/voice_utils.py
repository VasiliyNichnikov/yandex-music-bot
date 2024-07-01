import typing

import discord
from discord.ext import commands

from core.thread import ThreadManager


async def try_to_connect_to_voice_channel(thread_manager: ThreadManager,
                                          context: commands.Context | discord.Interaction,
                                          ignore_user_in_voice_channel: bool = False) -> typing.Tuple[bool, str | None]:
    guild_id: int = 0
    voice_channel: discord.VoiceChannel | None = None

    if isinstance(context, commands.Context):
        if context.author.voice is None or context.author.voice.channel is None:
            return False, "user_is_not_in_channel"

        guild_id = context.guild.id
        voice_channel = context.author.voice.channel

    if isinstance(context, discord.Interaction):
        if context.user.voice is None or context.user.voice.channel is None:
            return False, "user_is_not_in_channel"

        guild_id = context.guild.id
        voice_channel = context.user.voice.channel

    thread = thread_manager.get_thread_by_guild_id(guild_id)
    if thread is None:
        return False, "thread_not_found"

    if thread.player.is_running() and ignore_user_in_voice_channel:
        return True, None

    if voice_channel is None:
        return False, "user_is_not_in_channel"

    result = await thread.try_to_connect_to_voice_channel(voice_channel)
    message = None if result else "unable_to_connect_to_voice_channel"
    return result, message
