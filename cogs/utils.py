from discord.ext import commands

from bot import CactusDiscordBot
from cogs.commands import recreate_command
from core.wrappers import ContextWrapper


@commands.guild_only()
class Utils(commands.Cog):

    def __init__(self, bot: CactusDiscordBot) -> None:
        self._bot = bot

    @commands.command(name="recreate")
    async def recreate(self, context: commands.Context) -> None:
        wrapper = ContextWrapper(context)
        await recreate_command(wrapper, self._bot)


async def setup(bot: CactusDiscordBot) -> None:
    await bot.add_cog(Utils(bot))
