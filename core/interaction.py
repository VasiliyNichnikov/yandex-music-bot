import typing
from typing import Optional, Any, Sequence

from discord import AllowedMentions, Embed, File
from discord.ui import View


class SenderMessages(typing.Protocol):
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
        raise NotImplemented


class SenderMessagesWithGuild(SenderMessages):
    @property
    def guild_id(self) -> int:
        raise NotImplemented

