"""
    Отвечает за отправку сообщений и их удаление
"""
import typing

import discord

from core.config import ConfigManager
from core.interaction import SenderMessages
from core.log_utils import get_logger
from core.reading_time_calculator import get_reading_time

logger = get_logger(__name__)


class MessageManager:
    def __init__(self, config: ConfigManager) -> None:
        self.__message_lifetime = config["message_lifetime"]

    async def send_message(self, interaction: SenderMessages,
                           content: str | None = None,
                           tts: bool = False,
                           embed: discord.Embed | None = None,
                           embeds: typing.Sequence[discord.Embed] | None = None) -> None:
        text: str | None = self.__get_text_in_message(content, embed, embeds)
        delete_after = get_reading_time(text) if text is not None else self.__message_lifetime
        logger.debug(f"Text: {text}; Delete after: {delete_after}.")

        if embed is not None:
            await interaction.send_message(content=content, tts=tts, embed=embed, delete_after=delete_after)
            return
        if embeds is not None:
            await interaction.send_message(content=content, tts=tts, embeds=embeds, delete_after=delete_after)
            return
        await interaction.send_message(content=content, tts=tts, delete_after=delete_after)

    async def send_message_text_channel(self, text_channel: discord.TextChannel,
                                        content: str | None = None,
                                        tts: bool = False,
                                        embed: discord.Embed | None = None,
                                        embeds: typing.Sequence[discord.Embed] | None = None) -> None:
        text: str | None = self.__get_text_in_message(content, embed, embeds)
        delete_after: float = get_reading_time(text) if text is not None else self.__message_lifetime
        logger.debug(f"Text: {text}; Delete after: {delete_after}")
        await text_channel.send(content=content, tts=tts, embed=embed, delete_after=delete_after)

    @staticmethod
    async def delete(message: discord.Message) -> None:
        try:
            await message.delete()
        except discord.errors.NotFound:
            logger.warning(f"The message {message.id} has already been deleted.")
        except discord.errors.Forbidden:
            logger.error("Insufficient permissions to delete a message.")
            logger.debug(f"Message data. Author: {message.author}; content: {message.content}")

    @staticmethod
    def __get_text_in_message(content: str | None, embed: discord.Embed | None,
                              embeds: typing.Sequence[discord.Embed] | None) -> str:
        def get_text_from_embed(embed: discord.Embed) -> str:
            embed_text = ""
            if embed.title is not None:
                embed_text += embed.title
            if embed.description is not None:
                embed_text += " " + embed.description
            return embed_text

        text = ""
        if content is not None:
            text += content
        if embed is not None:
            text += " " + get_text_from_embed(embed)
        if embeds is not None:
            for embed in embeds:
                text += " " + get_text_from_embed(embed)
        return text if text != "" else None
