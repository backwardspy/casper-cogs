from redbot.core import commands

from meatballday.cog import MeatballDay


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MeatballDay(bot))
