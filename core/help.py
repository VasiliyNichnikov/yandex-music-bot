import typing
from typing import Any, Mapping, Optional, List

import discord
from discord.ext import commands
from discord.ext.commands import Cog, Command

from core._color_data import DISCORD_COLORS
from core.config import ConfigManager
from core.log_utils import get_logger
from core.message_manager import MessageManager
from core.wrappers import ContextWrapper

logger = get_logger(__name__)


class CactusDiscordHelpCommand(commands.HelpCommand):
    def __init__(self, config: ConfigManager, message_manager: MessageManager, **options: Any):
        self._config = config
        self._message_manager = message_manager
        super().__init__(**options)

        messages = self._config["messages"]
        self._command_description_not_found = messages["command_description_not_found"]
        self._name_commands_and_description = {
            "fh": messages["favorite_command_description"],
            "url": messages["url_command_description"],
            "sh": messages["search_command_description"],
            "recreate": messages["recreate_command_description"],
            "prev": messages["previous_command_description"],
            "next": messages["next_command_description"],
            "loop": messages["loop_command_description"],
            "pause": messages["pause_command_description"],
            "stop": messages["stop_command_description"],
            "queue": messages["queue_command_description"],
            "play": messages["play_command_description"]
        }

    async def send_bot_help(self, mapping: Mapping[Optional[Cog], List[Command[Any, ..., Any]]]) -> None:
        context = self.context
        bot = context.bot

        description: typing.List = []
        for command in bot.all_commands:
            if command.lower() == "help":
                continue

            available_command: bool | None = self._config.get_unsafe(command)
            if available_command is not None and not  available_command:
                continue

            command_ext = bot.get_command(command)
            description_command = self.__get_description_for_command(command)
            info_about_command = f"**{command_ext.name}** - {description_command}"
            description.append(info_about_command)
        await self.__send_message(self._config["messages"]["help_title"], '\n'.join(description))

    async def send_command_help(self, command: Command[Any, ..., Any]) -> None:
        description_command = self.__get_description_for_command(command.name)
        info_about_command = f"**{command.name}** - {description_command}"
        await self.__send_message(self._config["messages"]["help_title"], info_about_command)

    async def send_cog_help(self, cog: Cog) -> None:
        print("Sending in cog help")

    async def send_error_message(self, error: str) -> None:
        error_message = self._config["messages"]["error_message_in_command"].format(error=error)
        await self.__send_message(title=self._config["messages"]["help_error_title"], content=error_message)

    async def __send_message(self, title: str, content: str, color=DISCORD_COLORS["orange"]) -> None:
        embed = discord.Embed(title=title, description=content, colour=color)
        embed.set_author(name="CactusBot")
        wrapper = ContextWrapper(self.context)
        await self._message_manager.send_message(wrapper, embed=embed)

    def __get_description_for_command(self, name_command: str) -> str:
        if name_command not in self._name_commands_and_description:
            logger.error(f"Description for command {name_command} not found.")
            return self._command_description_not_found
        return self._name_commands_and_description[name_command]
