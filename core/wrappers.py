from typing import Optional, Any, Sequence

from discord import InteractionResponse, Embed, File, AllowedMentions
from discord.ext import commands
from discord.ui import View
from discord.utils import MISSING

from core.interaction import SenderMessagesWithGuild


class InteractionWrapper(SenderMessagesWithGuild):
    def __init__(self, interaction: InteractionResponse, guild_id: int) -> None:
        self._interaction = interaction
        self._guild_id = guild_id

    @property
    def guild_id(self) -> int:
        return self._guild_id

    async def send_message(
            self,
            content: Optional[Any] = None,
            *,
            embed: Embed = MISSING,
            embeds: Sequence[Embed] = MISSING,
            file: File = MISSING,
            files: Sequence[File] = MISSING,
            view: View = MISSING,
            tts: bool = False,
            ephemeral: bool = False,
            allowed_mentions: AllowedMentions = MISSING,
            suppress_embeds: bool = False,
            silent: bool = False,
            delete_after: Optional[float] = MISSING,
    ) -> None:
        await self._interaction.send_message(content,
                                             embed=embed,
                                             embeds=embeds,
                                             file=file,
                                             files=files,
                                             view=view,
                                             tts=tts,
                                             ephemeral=ephemeral,
                                             allowed_mentions=allowed_mentions,
                                             silent=silent,
                                             delete_after=delete_after)


class ContextWrapper(SenderMessagesWithGuild):
    def __init__(self, context: commands.Context):
        self._context = context

    @property
    def guild_id(self) -> int:
        return self._context.guild.id

    async def send_message(
            self,
            content: Optional[Any] = None,
            *,
            embed: Embed = None,
            embeds: Sequence[Embed] = None,
            file: File = None,
            files: Sequence[File] = None,
            view: View = None,
            tts: bool = False,
            ephemeral: bool = False,
            allowed_mentions: AllowedMentions = None,
            suppress_embeds: bool = False,
            silent: bool = False,
            delete_after: Optional[float] = None, ) -> None:
        await self._context.send(content,
                                 embed=embed,
                                 embeds=embeds,
                                 file=file,
                                 files=files,
                                 view=view,
                                 tts=tts,
                                 ephemeral=ephemeral,
                                 allowed_mentions=allowed_mentions,
                                 silent=silent,
                                 delete_after=delete_after)
