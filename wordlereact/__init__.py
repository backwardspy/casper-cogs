from redbot.core import commands

from wordlereact.cog import WordleReact


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WordleReact(bot))
