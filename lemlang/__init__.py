from redbot.core import commands

from lemlang.cog import Lemlang


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Lemlang(bot))
