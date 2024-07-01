import typing

import discord
from discord import app_commands
from discord.ext import commands

from bot import CactusDiscordBot
from cogs.commands import favorite_command, url_command, search_command, play_command
from core.log_utils import get_logger
from core.voice_utils import try_to_connect_to_voice_channel
from core.wrappers import InteractionWrapper
from requests_to_music_service.executing_requests import ExecutingRequests
from storage.data import TrackData
from storage.storage import Storage
from yandex.utils import get_track_wrapper, is_yandex_music_url

logger = get_logger(__name__)


@app_commands.guild_only()
class MusicSlash(commands.Cog, name="music_slash"):
    def __init__(self, bot: CactusDiscordBot) -> None:
        self._bot = bot
        super().__init__()

    # @app_commands.command(name="fh", description="Включает ваши любимые треки") # Команда отключена
    async def _favorite(self, interaction: discord.Interaction) -> None:
        state = await self.__validation_and_send_message(interaction)
        if not state:
            return
        logger.debug("Run favorite command")
        wrapper = InteractionWrapper(interaction.response, interaction.guild_id)
        await favorite_command(wrapper, self._bot)

    # @app_commands.command(name="url", description="Включает треки по ссылке из Яндекс.Музыка")  # Команда отключена
    async def _url(self, interaction: discord.Interaction, url: str) -> None:
        state = await self.__validation_and_send_message(interaction)
        if not state:
            return

        logger.debug("Run url command")
        wrapper = InteractionWrapper(interaction.response, interaction.guild_id)
        await url_command(wrapper, self._bot, url)

    # @app_commands.command(name="sh", description="Включает треки используя поиск Яндекс.Музыка")  # Команда отключена
    async def _search(self, interaction: discord.Interaction, search: str) -> None:
        state = await self.__validation_and_send_message(interaction)
        if not state:
            return

        logger.debug("Run search command")
        wrapper = InteractionWrapper(interaction.response, interaction.guild_id)
        await search_command(wrapper, self._bot, search)

    @app_commands.command(name="play", description="Проигрывает треки по ссылке или используя поиск Яндекс")
    async def _play(self, interaction: discord.Interaction, search: str) -> None:
        state = await self.__validation_and_send_message(interaction)
        if not state:
            return

        logger.debug("Run play command")
        wrapper = InteractionWrapper(interaction.response, interaction.guild_id)
        await play_command(wrapper, self._bot, search)

    # @_search.autocomplete("search")  # Команда отключена
    async def __search_autocomplete(self, interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice]:
        if current is None:
            return []

        if len(current) < 1:
            return []

        result = await self.__search_tracks(current)
        return result

    @_play.autocomplete("search")
    async def __play_autocomplete(self, interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice]:
        """
            Логика следующая:
            Изначально показываем сохраненные данные из БД (предыдущие запросы) с названием того, что будет включено
            Если пользователь начинает писать текст, ищем данные в Яндекс.Поиск
        """
        thread = self._bot.thread_manager.get_thread_by_guild_id(interaction.guild_id)
        if thread is None:
            logger.error("play_autocomplete: thread is None")
            return []

        if is_yandex_music_url(current):
            return []

        result: typing.List[app_commands.Choice] = []
        recent_requests = thread.get_recent_requests()
        if (current is None or len(current) < 1) and len(recent_requests) != 0:
            for recent_request in recent_requests:
                choice = app_commands.Choice(name=recent_request.title, value=recent_request.content)
                result.append(choice)
            return result

        if current is None or len(current) < 0 or current == "":
            return []

        result = await self.__search_tracks(current)
        return result

    async def __search_tracks(self, request: str) -> typing.List[app_commands.Choice]:
        search_request = self._bot.yandex_music_api.get_request_by_search(request, max_tracks=10)
        executing = ExecutingRequests(number_of_attempts=5, delay_between_errors=5)
        storage = Storage(executing)
        await storage.add(search_request)

        tracks: typing.Tuple[TrackData] = storage.get_tracks_range(0, 10)
        if len(tracks) == 0:
            return []

        wrappers = [get_track_wrapper(track, storage) for track in tracks]
        result: typing.List[app_commands.Choice] = []
        for track in wrappers:
            choice = app_commands.Choice(name=track.get_name_to_search(), value=track.url)
            result.append(choice)
        return result

    async def __validation_and_send_message(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.response, discord.InteractionResponse):
            return False

        state, message_key = await try_to_connect_to_voice_channel(self._bot.thread_manager,
                                                                   interaction,
                                                                   self._bot.config["ignore_user_in_voice_channel"])

        if message_key is not None:
            content = self._bot.config["messages"][message_key]
            wrapper = InteractionWrapper(interaction.response, interaction.guild.id)
            await self._bot.message_manager.send_message(wrapper, content=content)
        return state


async def setup(bot: CactusDiscordBot) -> None:
    await bot.add_cog(MusicSlash(bot))
    all_commands = await bot.tree.sync()
    for command in all_commands:
        bot.add_slash_command_data(command.name, command.id)
