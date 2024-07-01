from discord.ext import commands

from bot import CactusDiscordBot
from cogs.commands import previous_command, next_command, loop_command, pause_command, stop_command
from core.permissions import player_permissions
from core.playerfacade import PlayerFacade
from core.errors import BotIsNotRunningError
from core.wrappers import ContextWrapper


@commands.guild_only()
class Player(commands.Cog):
    def __init__(self, bot: CactusDiscordBot):
        self._bot = bot

    @commands.command(name="prev")
    @commands.bot_has_guild_permissions(**player_permissions)
    async def preview(self, context: commands.Context) -> None:
        player = self.__get_player_with_error_if_contains(context.guild.id)
        if player is None:
            return

        wrapper = ContextWrapper(context)
        await previous_command(wrapper, self._bot, player)

    @commands.command(name="next")
    @commands.bot_has_guild_permissions(**player_permissions)
    async def next(self, context: commands.Context) -> None:
        player = self.__get_player_with_error_if_contains(context.guild.id)
        if player is None:
            return

        wrapper = ContextWrapper(context)
        await next_command(wrapper, self._bot, player)

    @commands.command(name="loop")
    @commands.bot_has_guild_permissions(**player_permissions)
    async def loop(self, context: commands.Context) -> None:
        player = self.__get_player_with_error_if_contains(context.guild.id)
        if player is None:
            return

        wrapper = ContextWrapper(context)
        await loop_command(wrapper, self._bot, player)

    @commands.command(name="pause")
    @commands.bot_has_guild_permissions(**player_permissions)
    async def pause(self, context: commands.Context) -> None:
        player = self.__get_player_with_error_if_contains(context.guild.id)
        if player is None:
            return

        wrapper = ContextWrapper(context)
        await pause_command(wrapper, self._bot, player)

    @commands.command(name="stop")
    @commands.bot_has_guild_permissions(**player_permissions)
    async def stop(self, context: commands.Context) -> None:
        player = self.__get_player_with_error_if_contains(context.guild.id)
        if player is None:
            return

        wrapper = ContextWrapper(context)
        await stop_command(wrapper, self._bot, player)

    @commands.command(name="queue")
    @commands.bot_has_guild_permissions(**player_permissions)
    async def queue(self, context: commands.Context) -> None:
        """
            Текущая команда поддерживается пока только для обычных команд
            Без использования слэша
        """
        player = self.__get_player_with_error_if_contains(context.guild.id)
        if player is None:
            return

        await player.show_track_queue()

    def __get_player_with_error_if_contains(self, guild_id: int) -> PlayerFacade | None:
        thread = self._bot.thread_manager.get_thread_by_guild_id(guild_id)

        if thread is None:
            return None

        if not thread.player.is_running():
            raise BotIsNotRunningError(f"Guild id: {guild_id}. Bot is not running in voice channel.")

        return thread.player


async def setup(bot: CactusDiscordBot) -> None:
    await bot.add_cog(Player(bot))
