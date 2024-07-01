import discord
from discord.ext import commands


class InvalidConfigError(commands.BadArgument):
    def __init__(self, message, *args) -> None:
        super(InvalidConfigError, self).__init__(message, *args)
        self._message = message

    @property
    def embed(self) -> discord.Embed:
        return discord.Embed(title="Error", description=self._message, color=discord.Color.red())


class VoiceChannelWithUserNotFoundError(commands.ChannelNotFound):
    pass


class BotIsNotRunningError(commands.CommandError):
    pass


class PlayerCriticalError(commands.CommandError):
    pass


class ThreadNotFoundError(commands.CommandError):
    pass


class InsufficientPermissionsToExecuteCommand(commands.CommandError):
    pass
