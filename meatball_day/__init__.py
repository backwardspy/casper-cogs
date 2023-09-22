from redbot.core import commands

from meatball_day.meatball_day import MeatballDay


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MeatballDay(bot))
