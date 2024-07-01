"""
    Иеди по реализации взяты от сюда:
    https://github.innominds.com/modmail-dev/Modmail/tree/master
"""

__version__ = "0.0.1"

import asyncio
import sys
import traceback
import typing

import discord
from discord.ext import commands, tasks

from cogs.cache import InitializedSlashCommands
from cogs.errors import CommandIsNotAvailable
from core.config import ConfigManager
from core.errors import VoiceChannelWithUserNotFoundError, BotIsNotRunningError, PlayerCriticalError, \
    InsufficientPermissionsToExecuteCommand
from core.log_utils import get_logger
from core.wrappers import ContextWrapper
from utils.taskmanager.protocols import TaskManagerProtocol
from utils.taskmanager.taskmanager import TaskManager
from core.thread import ThreadManager
from yandex.client import YandexMusicBase, YandexMusicAccount
from core.help import CactusDiscordHelpCommand
from core.message_manager import MessageManager
from core.factories import BotFactory
from database.clients import ClientDataBaseAPI

logger = get_logger(__name__)

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except AttributeError:
        logger.error("Failed to use WindowsProactorEventLoopPolicy.", exc_info=True)


class CactusDiscordBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.all()

        self._connected: asyncio.Event | None = None
        self._config = ConfigManager()
        self._config.init_cache()
        self._message_manager = MessageManager(self._config)
        help_command = CactusDiscordHelpCommand(self._config, self._message_manager)

        super().__init__(command_prefix=self._config["prefix"], help_command=help_command, intents=intents)

        self._thread_manager = ThreadManager(self)
        self._yandex_music = YandexMusicAccount(self._config)
        self.__loaded_cogs = ["cogs.music", "cogs.player", "cogs.utils"]
        if self._config["slash_supported"]:
            self.__loaded_cogs.extend(["cogs.musicslash", "cogs.playerslash", "cogs.utilsslash"])
        self._database_api = ClientDataBaseAPI(self._config)
        self._bot_factory = BotFactory(self, self._config)
        self._task_manager: TaskManager = TaskManager()
        self._bot_is_running: bool = False
        # Все команды через слеш
        self._initialized_slash_commands: InitializedSlashCommands = InitializedSlashCommands(self._config)

    @property
    def bot_owner_ids(self) -> typing.Set[int]:
        owner_bot_id = self.config["owner_bot_id"]
        if owner_bot_id is not None:
            try:
                owner_bot_id = int(owner_bot_id)
            except Exception as e:
                logger.error(f"owner_bot_id: error during conversion: {e}")
                return set()
            return {owner_bot_id}
        return set()

    @property
    def slash_commands(self) -> InitializedSlashCommands:
        return self._initialized_slash_commands

    @property
    def bot_token(self) -> str:
        """
            Токен дискорд бота
        """
        token = self._config["discord_token"]
        if token is None:
            logger.critical("TOKEN must be set, set this as bot token found on the Discord Developer Portal")
            sys.exit(0)
        return token

    @property
    def yandex_music_api(self) -> YandexMusicBase:
        """
            Данные для работы с библиотекой Я.Музыка
            На текущий момент меня устраивает ситуация
            при которой музыка берется с одного API
            Если нужно будет расширяться, то логично чтобы API
            У каждого канала было свое
        """
        return self._yandex_music

    @property
    def factory(self) -> BotFactory:
        return self._bot_factory

    @property
    def database_api(self) -> ClientDataBaseAPI:
        return self._database_api

    @property
    def message_manager(self) -> MessageManager:
        """
            Пока внутри содержит статичные методы
            Но в будущем может будет расширяться, поэтому пусть будет один на всех
        """
        return self._message_manager

    @property
    def thread_manager(self) -> ThreadManager:
        return self._thread_manager

    @property
    def config(self) -> ConfigManager:
        return self._config

    @property
    def task_manager(self) -> TaskManagerProtocol:
        return self._task_manager

    async def is_owner(self, user: discord.User) -> bool:
        if user.id in self.bot_owner_ids:
            return True
        return await super().is_owner(user)

    def is_owner_bot(self, user: discord.User | discord.Member) -> bool:
        if not user.bot:
            return False
        return user.id in self.bot_owner_ids

    def add_slash_command_data(self, command_name: str, command_id: int) -> None:
        self._initialized_slash_commands.add_command(command_name, command_id)

    def run(self) -> None:
        async def runner():
            async with self:
                self._connected = asyncio.Event()

                try:
                    await self.start(self.bot_token)
                except discord.PrivilegedIntentsRequired:
                    logger.critical(
                        "Privileged intents are not explicitly granted in the discord developers dashboard.")
                except discord.LoginFailure:
                    logger.critical("Invalid token")
                    pass
                except Exception:
                    logger.critical("Fatal exception", exc_info=True)
                finally:
                    pass

        async def _cancel_tasks() -> None:
            async with self:
                task_retriever = asyncio.all_tasks
                loop = self.loop
                tasks = {task for task in task_retriever() if not task.done() and task.get_coro() != cancel_tasks_coro}

                if not tasks:
                    return

                logger.info(f"Cleaning up after {len(tasks)} tasks.")
                for task in tasks:
                    task.clean()

                # Одновременно запускает объекты awaitable, переданные в функцию как последовательность *aws.
                await asyncio.gather(*tasks, return_exceptions=True)
                logger.info("All tasks finished cancelling.")

                for task in tasks:
                    try:
                        if task.exception() is not None:
                            loop.call_exception_handler(
                                {
                                    "message": "Unhandled exception during Client.run shutdown.",
                                    "exception": task.exception(),
                                    "task": task,
                                }
                            )
                    except (asyncio.InvalidStateError, asyncio.CancelledError):
                        pass

        try:
            asyncio.run(runner())
        except (KeyboardInterrupt, SystemExit):
            logger.info("Received signal to terminal bot and event loop.")
        finally:
            logger.info("Cleaning up tasks.")

            try:
                self._bot_is_running = False
                cancel_tasks_coro = _cancel_tasks()
                asyncio.run(cancel_tasks_coro)
            finally:
                logger.info("Closing the event loop.")

    async def on_ready(self) -> None:
        """
            Срабатывает когда бот запущен
        """
        if self._bot_is_running:
            logger.info("on_ready: the bot is already running and runs the on_ready command.")
            return

        await self.__wait_for_connected()

        await self._thread_manager.init()

        self.autoupdate.start()
        self.__process_task_manager.start()
        logger.info("Bot is ready to work.")
        self._bot_is_running = True

    async def on_connect(self) -> None:
        await self.load_extensions()
        await self._yandex_music.init()
        self._connected.set()
        logger.debug("Connected to gateway.")

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """
            Регистрируем пользователя
        """
        await self._thread_manager.add_thread_by_guild_id(guild)

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """
            Удаляем пользователя
        """
        self._thread_manager.remove_thread_by_guild_id(guild.id)

    async def on_message(self, message: discord.Message) -> None:
        """
            Обработка сообщений в канале
        """
        await self.__wait_for_connected()

        if message.is_system():
            return

        if self.is_owner_bot(message.author):
            return

        thread = self.thread_manager.get_thread_by_guild_id(message.guild.id)
        if thread is None:
            return

        available_command = await self.__is_command_available_everywhere(message)
        if not thread.view.is_initialized and available_command:
            context = await self.get_context(message)
            self.dispatch("command_error", context, InsufficientPermissionsToExecuteCommand())
            return

        if not thread.view.is_text_channel_with_music(message.channel.id) and not available_command:
            return

        await self.process_commands(message)
        # Костыль, но по нормальному проверить права не получается
        await self._message_manager.delete(message)

    async def process_commands(self, message: discord.Message) -> None:
        """
            Обработка команд, которые приходят боту через "!"
        """
        if self.is_owner_bot(message.author):
            return

        ctx = await self.get_context(message)
        if ctx.command:
            await self.invoke(ctx)
            return
        elif ctx.invoked_with:
            exc = commands.CommandNotFound('Command "{}" is not found.'.format(ctx.invoked_with))
            self.dispatch("command_error", ctx, exc)

    async def try_search_and_complete_command(self, cog_name: str, command_name: str,
                                              data: discord.Interaction | discord.Message) -> None:
        try:
            context = await self.get_context(data)
        except Exception as e:
            logger.critical(f"Couldn't get the context: {e}")
            return

        if context is None:
            return

        cog = self.get_cog(cog_name)
        for command in cog.get_commands():
            if command.name == command_name:
                try:
                    await command.invoke(context)
                except commands.CommandError as command_error:
                    self.dispatch("command_error", context, command_error)
                return

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        logger.error(f"Ignoring exception in {event_method}")
        logger.error(f"Unexpected exception: {sys.exc_info()}; Traceback: {traceback.format_stack()}")

    async def on_command_error(self, context: commands.Context, exception: commands.CommandError) -> None:
        """
            Обработка ошибок от команд
        """
        logger.debug(f"Exception command: {exception.__class__.__name__}: {exception}")

        message: str | None = None
        need_show_message: bool = True
        if isinstance(exception, VoiceChannelWithUserNotFoundError):
            message = self._config["messages"]["user_is_not_in_channel"]
        elif isinstance(exception, commands.MissingPermissions):
            message = self._config["messages"]["missing_permissions"]
        elif isinstance(exception, commands.CommandNotFound):
            message = self._config["messages"]["command_not_found"]
        elif isinstance(exception, commands.MissingRequiredArgument):
            need_show_message = False
            await context.send_help(context.command)
        elif isinstance(exception, BotIsNotRunningError):
            message = self._config["messages"]["player_is_not_running"]
        elif isinstance(exception, commands.BadArgument):
            message = self._config["messages"]["bad_argument"]
        elif isinstance(exception, PlayerCriticalError):
            message = self._config["messages"]["player_critical_error"]
        elif isinstance(exception, commands.BotMissingPermissions):
            message = self._config["messages"]["bot_missing_permissions"]
        elif isinstance(exception, InsufficientPermissionsToExecuteCommand):
            message = self._config["messages"]["no_permissions_to_execute_command"]
            permissions_manage_channels = self._config["messages"]["permissions_manage_channels"]
            permissions_send_messages = self._config["messages"]["permissions_send_messages"]
            permissions_manage_messages = self._config["messages"]["permissions_manage_messages"]
            permissions = '\n'.join((permissions_manage_channels, permissions_send_messages, permissions_manage_messages))
            message = str.format(message, permissions)
        elif isinstance(exception, CommandIsNotAvailable):
            message = self._config["messages"]["command_is_not_available_to_enable"]

        if message is not None and need_show_message:
            wrapper = ContextWrapper(context)
            await context.typing()
            await self._message_manager.send_message(wrapper, embed=discord.Embed(color=discord.Color.red(), description=message))
        elif message is None and need_show_message:
            logger.error("Unexpected exception:", exc_info=exception)

    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState) -> None:
        # TODO: по хорошему почистить метод. Слишком много того, что надо спрятать
        thread = self._thread_manager.get_thread_by_guild_id(member.guild.id)
        if thread is None:
            return

        if self.is_owner_bot(member) and member.bot:
            # Бот покинул канал. Это может быть связано из-за отключение бота с помощью панели в дискорде
            # Пока все равно не исправлена нормально
            if before.channel is not None and after.channel is None:
                if thread.can_run_unsafe_disconnection:
                    await thread.unsafe_disconnection_from_voice_channel()
            # Бота перенесли в другой канал
            elif before.channel is not None and after.channel is not None:
                voice_client: discord.VoiceClient | None = discord.utils.get(self.voice_clients, guild=member.guild)
                if voice_client is None:
                    return
                # Бот единственный в новом месте
                if not self._config["ignore_number_members_in_voice_chat"] and len(voice_client.channel.members) == 1:
                    await thread.try_to_disconnect_from_voice_channel()
                    return
                await thread.update_voice_client(voice_client)
            return

        if not self._config["ignore_number_members_in_voice_chat"]:
            if thread.in_voice_channel and thread.number_members_in_voice == 1:
                await thread.try_to_disconnect_from_voice_channel()

    @tasks.loop(hours=1)
    async def autoupdate(self) -> None:
        """
            Код вызывается раз в час
        """
        await self._thread_manager.update_thread()

    @tasks.loop(seconds=1)
    async def __process_task_manager(self) -> None:
        await self._task_manager.process()

    async def load_extensions(self) -> None:
        for cog in self.__loaded_cogs:
            if cog in self.extensions:
                continue
            logger.debug(f"Loading {cog}.")
            try:
                await self.load_extension(cog)
                logger.debug(f"Successfully loaded {cog}.")
            except Exception:
                logger.exception(f"Failed to load {cog}.")

    async def __is_command_available_everywhere(self, message: discord.Message) -> bool:
        if message is None:
            return False

        ctx = await self.get_context(message)
        if ctx.command:
            return ctx.command.name in self.config["commands_that_ignore_music_text_channel"]
        return False

    async def __wait_for_connected(self) -> None:
        await self.wait_until_ready()
        await self._connected.wait()
