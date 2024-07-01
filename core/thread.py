"""
    Осуществляем работу с пользователями
"""
import datetime
import typing

import discord.errors
from discord import Guild, VoiceChannel, VoiceClient

from cogs.cache import InitializedSlashCommands
from core.config import ConfigManager
from core.factories import BotFactory
from core.log_utils import get_logger
from core.message_manager import MessageManager
from core.playerfacade import PlayerFacade
from core.recentrequest import RecentRequestProtocol
from core.view import DiscordViewHelper
from database.clients import ThreadDataBase
from permissions.errors import FailedToInitializeDiscordViewHelper
from requests_to_music_service.data import InfoAboutRequest

logger = get_logger(__name__)


class UserThread:
    def __init__(self, guild: Guild,
                 thread_db_api: ThreadDataBase,
                 config: ConfigManager,
                 factory: BotFactory,
                 message_manager: MessageManager,
                 slash_commands: InitializedSlashCommands) -> None:
        self._guild: Guild = guild
        self._disconnection_timer = factory.create_timer(config["waiting_time_before_disconnection"])

        self._current_voice_client: VoiceClient | None = None
        self._config = config
        self._running_unsafe_disconnection: bool = False

        self._db = thread_db_api
        self._factory: BotFactory = factory

        self._view: DiscordViewHelper = self.__create_discord_view()
        self._player_facade: PlayerFacade = factory.create_player(self._disconnection_timer, self._view, self.__add_request_to_database)
        self._message_manager: MessageManager = message_manager
        self._slash_commands = slash_commands

    @property
    def view(self) -> DiscordViewHelper:
        return self._view

    @property
    def number_members_in_voice(self) -> int:
        if self._current_voice_client is None:
            logger.error("Voice client is None.")
            return 0
        if not self._current_voice_client.is_connected():
            logger.error("Voice client is not connected.")
            return 0
        return len(self._current_voice_client.channel.voice_states)

    @property
    def player(self) -> PlayerFacade:
        return self._player_facade

    @property
    def can_run_unsafe_disconnection(self) -> bool:
        return not self._running_unsafe_disconnection and self._current_voice_client is not None

    @property
    def config(self) -> ConfigManager:
        return self._config

    @property
    def guild(self) -> Guild:
        """
            Может не самое удачное решение отдавать гилдию всем подряд
        """
        return self._guild

    @property
    def message_manager(self) -> MessageManager:
        return self._message_manager

    @property
    def in_voice_channel(self) -> bool:
        return self._current_voice_client is not None

    @property
    def slash_commands(self) -> InitializedSlashCommands:
        return self._slash_commands

    def get_recent_requests(self) -> typing.Tuple[RecentRequestProtocol, ...]:
        """
            Может не самое удачное решение выдавать их из треда, но другое место пока не придумал
        """
        recent_requests = self._db.get_all_recent_requests()

        sorted_recent_requests = tuple(sorted(recent_requests, key=lambda request: request.date_time, reverse=True))
        max_recommendations = self._config["maximum_number_recent_requests_in_message"]
        return sorted_recent_requests[:max_recommendations]

    async def init(self) -> None:
        data = self._db.guild_data

        self._disconnection_timer.set_invoke(self.try_to_disconnect_from_voice_channel)
        try:
            await self._view.init_text_channel_and_history_thread(data.text_channel_id, data.thread_id)
            await self._view.update_cover_to_default()
        except FailedToInitializeDiscordViewHelper:
            logger.warning(f"init: Not enough permissions to init view ({self.guild.name}).")
        except discord.errors.Forbidden as e:
            logger.error(f"init: Not enough permissions to init view ({self.guild.name}); Exception: {e}.")

    async def update(self) -> None:
        """
            Во время обновления проверяем существования канала и ветки
        """
        if not self._view.is_initialized:
            return

        await self._view.check_existence_of_text_channel_and_thread()
        if not self._player_facade.is_running():
            await self._view.update_cover_to_default()

    async def try_to_connect_to_voice_channel(self, voice_channel: VoiceChannel) -> bool:
        if voice_channel is None:
            logger.error("You cannot connect to None")
            return False

        if self._current_voice_client is not None:
            if self._current_voice_client.channel.id == voice_channel.id:
                return True
            if self._current_voice_client.is_connected():
                await self._player_facade.stop_track(disconnect=True)
                await self._current_voice_client.disconnect()
                self._current_voice_client = None
        try:
            self._current_voice_client = await voice_channel.connect(timeout=10, reconnect=False, self_mute=True, self_deaf=True)
            self._player_facade.update_voice_client(self._current_voice_client)
            return True
        except discord.errors.ClientException as error:
            is_connected: bool = False
            if self._current_voice_client is not None:
                is_connected = self._current_voice_client.is_connected()
            logger.error(f"Trying to connect to voice: {error}; Voice client null: {self._current_voice_client is None}; Is connected: {is_connected}")
            return False

    async def try_to_disconnect_from_voice_channel(self) -> bool:
        if self._current_voice_client is None:
            logger.warning("Current voice client is None")
            return False
        try:
            await self._player_facade.stop_track(disconnect=True)
            await self._current_voice_client.disconnect()
            self._current_voice_client = None
            self._player_facade.update_voice_client(None)
            logger.info(f"Disconnected from voice channel. Guild id: {self._guild.id}. Name: {self._guild.name}.")
        except Exception as e:  # TODO: удалить. Пока для понимания проблемы
            logger.error(f"Failed to disconnect the voice channel: {e}. Guild id: {self._guild.id}. Name: {self._guild.name}.")
        return True

    async def update_voice_client(self, voice_channel: VoiceClient) -> None:
        """
            Отличие от try_to_connect_to_voice_channel,
            что в этом случае мы уже подкючены, но это сделал пользователь.
        """
        self._current_voice_client = voice_channel
        await self._player_facade.stop_track(disconnect=False, safely=False)
        self._player_facade.update_voice_client(self._current_voice_client)
        logger.info("Voice client has been updated.")

    async def unsafe_disconnection_from_voice_channel(self) -> None:
        """
            Небезопасное отключение подразумевает, что бот вышел не по собственному желанию,
            но запущенные процессы не были отключены.
        """
        if self._running_unsafe_disconnection:
            logger.error("Running unsafe disconnection is already running.")
            return

        self._running_unsafe_disconnection = True
        # fixme не работает, в таком случае нас отключает спустя время
        # self._current_voice_client.cleanup()
        try:
            await self._player_facade.stop_track(disconnect=True, safely=False)
            self._current_voice_client = None
            self._player_facade.update_voice_client(None)
            logger.info(f"(Unsafe) Disconnected from voice channel. Guild id: {self._guild.id}. Name: {self._guild.name}.")
        # Ошибка может возникнуть если во время проигрывания бота выгнали с сервера и on_voice_state_update сработал раньше удаления данных о канале
        except Exception as e:
            logger.error(f"Failed to (Unsafe) disconnect the voice channel: {e}; Guild id: {self._guild.id}. Name: {self._guild.name}.")
        finally:
            self._running_unsafe_disconnection = False

    def remove(self) -> None:
        """
            После того как бота выкинули, мы можем только удалить данные
        """
        self._db.delete()

    def __create_discord_view(self) -> DiscordViewHelper:
        helper = DiscordViewHelper(self, self._factory)
        helper.set_on_thread_created(self.__on_update_thread)
        helper.set_on_text_chanel_invoke(self.__on_update_text_channel)
        return helper

    def __on_update_thread(self, thread_id: int) -> None:
        self._db.update_history_thread(thread_id)

    def __on_update_text_channel(self, text_channel_id: int) -> None:
        self._db.update_channel_with_music(text_channel_id)

    def __add_request_to_database(self, data: InfoAboutRequest) -> None:
        self._db.add_music_request(data, datetime.datetime.now())


class ThreadManager:
    def __init__(self, bot: "CactusDiscordBot") -> None:
        self._bot = bot
        self._threads: typing.Dict = {}

    async def init(self) -> None:
        guilds = self._bot.guilds

        for guild in guilds:
            if guild.id in self._threads.keys():
                logger.error(f"Thread with id {guild.id} is already contains in dict.")
                continue
            thread: UserThread = self._bot.factory.create_thread(guild)
            self._threads[guild.id] = thread
            await thread.init()
            logger.info(f"Thread with id {guild.id} is initialized.")

        logger.info(f"Thread Manager initialized {len(guilds)} guilds.")

    async def update_thread(self) -> None:
        """
            Метод вызывается раз в N времени
            И может служить для проверки ключевых компонентов во время работы
        """
        for thread in self._threads.values():
            await thread.update()

    def get_thread_by_guild_id(self, guild_id: int) -> UserThread | None:
        if guild_id not in self._threads.keys():
            logger.error(f"Thread with id {guild_id} not found in dict.")
            return None
        return self._threads[guild_id]

    async def add_thread_by_guild_id(self, guild: Guild) -> None:
        guild_id = guild.id
        if guild_id in self._threads.keys():
            logger.error(f"Thread with id {guild_id} already exists.")
            return

        thread: UserThread = self._bot.factory.create_thread(guild)
        self._threads[guild.id] = thread
        await thread.init()

    def remove_thread_by_guild_id(self, guild_id: int) -> None:
        if guild_id not in self._threads.keys():
            logger.error(f"Thread with id {guild_id} not found in dict.")
            return

        thread: UserThread = self._threads[guild_id]
        thread.remove()
        del self._threads[guild_id]

