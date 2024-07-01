from discord.ext import commands

from bot import CactusDiscordBot
from cogs.commands import favorite_command, url_command, search_command, play_command
from core.log_utils import get_logger
from core.permissions import music_permissions
from core.voice_utils import try_to_connect_to_voice_channel
from core.wrappers import ContextWrapper
from cogs.checkers import check_availability_of_command

logger = get_logger(__name__)


@commands.guild_only()
class Music(commands.Cog, name="music"):
    def __init__(self, bot: CactusDiscordBot) -> None:
        self._bot = bot

    @commands.command(name="fh")
    @commands.bot_has_guild_permissions(**music_permissions)
    @check_availability_of_command()
    async def favorite(self, context: commands.Context) -> None:
        state = await self.__validation_and_send_message(context)
        if not state:
            return

        logger.debug("Run favorite command")
        wrapper = ContextWrapper(context)
        await favorite_command(wrapper, self._bot)

    @commands.command()
    @commands.bot_has_guild_permissions(**music_permissions)
    @check_availability_of_command()
    async def url(self, context: commands.Context, url: str) -> None:
        state = await self.__validation_and_send_message(context)
        if not state:
            return

        logger.debug("Run url command")
        wrapper = ContextWrapper(context)
        await url_command(wrapper, self._bot, url)

    @commands.command(name="sh")
    @commands.bot_has_guild_permissions(**music_permissions)
    @check_availability_of_command()
    async def search(self, context: commands.Context, *search_request_dirty: str) -> None:
        search_request = ' '.join(search_request_dirty)
        if not search_request:
            content = self._bot.config["messages"]["search_request_is_empty"]
            await self.__send_message(context, message=content)
            return

        state = await self.__validation_and_send_message(context)
        if not state:
            return

        logger.debug("Run search command")
        wrapper = ContextWrapper(context)
        await search_command(wrapper, self._bot, search_request)

    @commands.command(name="play")
    @commands.bot_has_guild_permissions(**music_permissions)
    @check_availability_of_command()
    async def play(self, context: commands.Context, *request_dirty: str) -> None:
        request = ' '.join(request_dirty)
        if not request:
            content = self._bot.config["messages"]["play_request_is_empty"]
            await self.__send_message(context, message=content)
            return

        state = await self.__validation_and_send_message(context)
        if not state:
            return

        logger.debug("Run play command")
        wrapper = ContextWrapper(context)
        await play_command(wrapper, self._bot, request)

    async def __validation_and_send_message(self, context: commands.Context) -> bool:
        state, message_key = await try_to_connect_to_voice_channel(self._bot.thread_manager,
                                                                   context,
                                                                   self._bot.config["ignore_user_in_voice_channel"])
        if message_key is not None:
            content = self._bot.config["messages"][message_key]
            await self.__send_message(context, message=content)
        return state

    async def __send_message(self, context: commands.Context, message: str) -> None:
        wrapper = ContextWrapper(context)
        await self._bot.message_manager.send_message(wrapper, content=message)


async def setup(bot: CactusDiscordBot) -> None:
    await bot.add_cog(Music(bot))
