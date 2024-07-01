import discord
from discord import app_commands
from discord.ext import commands

from bot import CactusDiscordBot
from cogs.commands import previous_command, next_command, loop_command, pause_command, stop_command
from core.playerfacade import PlayerFacade
from core.wrappers import InteractionWrapper


@app_commands.guild_only()
class PlayerSlash(commands.Cog, name="player_slash"):
    def __init__(self, bot: CactusDiscordBot) -> None:
        self._bot = bot
        super().__init__()

    @app_commands.command(name="previous", description="Включает предыдущий трек")
    async def _previous(self, interaction: discord.Interaction) -> None:
        player = await self.__get_player_with_error_if_contains(interaction)
        if player is None:
            return

        wrapper = InteractionWrapper(interaction.response, interaction.guild.id)
        await previous_command(wrapper, self._bot, player)

    @app_commands.command(name="next", description="Включает следующий трек")
    async def _next(self, interaction: discord.Interaction) -> None:
        player = await self.__get_player_with_error_if_contains(interaction)
        if player is None:
            return

        wrapper = InteractionWrapper(interaction.response, interaction.guild.id)
        await next_command(wrapper, self._bot, player)

    @app_commands.command(name="loop", description="Включает/Выключает зацикливание трека")
    async def _loop(self, interaction: discord.Interaction) -> None:
        player = await self.__get_player_with_error_if_contains(interaction)
        if player is None:
            return

        wrapper = InteractionWrapper(interaction.response, interaction.guild.id)
        await loop_command(wrapper, self._bot, player)

    @app_commands.command(name="pause", description="Включает/Выключает паузу у трека")
    async def _pause(self, interaction: discord.Interaction) -> None:
        player = await self.__get_player_with_error_if_contains(interaction)
        if player is None:
            return

        wrapper = InteractionWrapper(interaction.response, interaction.guild.id)
        await pause_command(wrapper, self._bot, player)

    @app_commands.command(name="stop", description="Удаляет все треки из очереди и выключает текущий трек")
    async def _stop(self, interaction: discord.Interaction) -> None:
        player = await self.__get_player_with_error_if_contains(interaction)
        if player is None:
            return

        wrapper = InteractionWrapper(interaction.response, interaction.guild.id)
        await stop_command(wrapper, self._bot, player)

    async def __get_player_with_error_if_contains(self, interaction: discord.Interaction) -> PlayerFacade | None:
        if not isinstance(interaction.response, discord.InteractionResponse):
            return None

        thread = self._bot.thread_manager.get_thread_by_guild_id(interaction.guild.id)

        if thread is None:
            return None

        if not thread.player.is_running():
            content = self._bot.config["messages"]["player_is_not_running"]
            wrapper = InteractionWrapper(interaction.response, interaction.guild.id)
            await self._bot.message_manager.send_message(wrapper, content=content)
            return None

        return thread.player


async def setup(bot: CactusDiscordBot) -> None:
    await bot.add_cog(PlayerSlash(bot))
    await bot.tree.sync()
