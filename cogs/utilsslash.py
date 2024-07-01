import discord
from discord import app_commands
from discord.ext import commands

from bot import CactusDiscordBot
from cogs.commands import recreate_command
from core.wrappers import InteractionWrapper


@app_commands.guild_only()
class UtilsSlash(commands.Cog, name="utils_slash"):
    def __init__(self, bot: CactusDiscordBot) -> None:
        self._bot = bot

    @app_commands.command(name="recreate", description="Пересоздает текстовый канал **Музыка** и ветку **Истории**")
    async def _recreate(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.response, discord.InteractionResponse):
            return
        wrapper = InteractionWrapper(interaction.response, interaction.guild.id)
        await recreate_command(wrapper, self._bot)


async def setup(bot: CactusDiscordBot) -> None:
    await bot.add_cog(UtilsSlash(bot))
    await bot.tree.sync()