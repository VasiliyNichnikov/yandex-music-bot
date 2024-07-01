import discord.ext.commands
from discord.ext.commands import Context

from cogs.errors import CommandIsNotAvailable
from core.log_utils import get_logger
from bot import CactusDiscordBot


logger = get_logger(__name__)


def check_availability_of_command():
    """
        Проверяем, доступна или нет команда для выполнения
    :return:
    """
    def predicate(context: Context) -> bool:
        if not isinstance(context.bot, CactusDiscordBot):
            logger.error(f"bot type is not corrected: {type(context.bot)}")
            return False

        config = context.bot.config
        if config.get_unsafe(context.command.name) is None:
            raise CommandIsNotAvailable(f"The command {context.command.name} is not available for playback")

        available_command = config[context.command.name]
        if not available_command:
            raise CommandIsNotAvailable(f"The command {context.command.name} is not available for playback")
        return True

    return discord.ext.commands.check(predicate)