import re

import discord
from redbot.core import commands


def re_compile(pattern: str) -> re.Pattern:
    """Compile a regex pattern."""
    return re.compile(pattern, re.IGNORECASE | re.MULTILINE)


reactions = [
    (re_compile(r"wordle \d+ [1-6]/6"), "🧠"),
    (re_compile(r"wordle \d+ 1/6"), "1️⃣"),
    (re_compile(r"wordle \d+ 2/6"), "2️⃣"),
    (re_compile(r"wordle \d+ X/6"), "🐌"),
    (re_compile(r"daily duotrigordle #\d+\nguesses: \d+/37"), "🧠"),
    (re_compile(r"daily duotrigordle #\d+\nguesses: X/37"), "🐌"),
    (re_compile(r"scholardle \d+ [1-6]/6"), "🎓"),
    (re_compile(r"scholardle \d+ 1/6"), "1️⃣"),
    (re_compile(r"scholardle \d+ 2/6"), "2️⃣"),
    (re_compile(r"scholardle \d+ X/6"), "🐌"),
    (re_compile(r"worldle #\d+ [1-6]/6 \(100%\)"), "🗺️"),
    (re_compile(r"worldle #\d+ X/6 \(\d+%\)"), "🐌"),
    (re_compile(r"waffle\d+ [0-5]/5"), "🧇"),
    (re_compile(r"waffle\d+ 5/5"), "⭐"),
    (re_compile(r"waffle\d+ X/5"), "🐌"),
    (re_compile(r"#wafflesilverteam"), "🥈"),
    (re_compile(r"#wafflegoldteam"), "🥇"),
    (re_compile(r"#wafflecenturion"), "🌟"),
    (re_compile(r"#wafflemaster"), "🏆"),
    (re_compile(r"flowdle \d+ \[\d+ moves\]"), "🚰"),
    (re_compile(r"flowdle \d+ \[failed\]"), "🐌"),
    (re_compile(r"jurassic wordle \(game #\d+\) - [1-8] / 8"), "🦕"),
    (re_compile(r"jurassic wordle \(game #\d+\) - X / 8"), "🐌"),
    (re_compile(r"jungdle \(game #\d+\) - [1-8] / 8"), "🦁"),
    (re_compile(r"jungdle \(game #\d+\) - X / 8"), "🐌"),
    (re_compile(r"dogsdle \(game #\d+\) - [1-8] / 8"), "🐶"),
    (re_compile(r"dogsdle \(game #\d+\) - X / 8"), "🐌"),
    (re_compile(r"framed #\d+.*\n+.*🎥 [🟥⬛ ]*🟩"), "🎬"),
    (re_compile(r"framed #\d+.*\n+.*🎥 [🟥⬛ ]+$"), "🐌"),
    (re_compile(r"moviedle #[\d-]+.*\n+.*🎥[🟥⬜⬛️ ]*🟩"), "🎬"),
    (re_compile(r"moviedle #[\d-]+.*\n+.*🎥[🟥⬜⬛️ ]+$"), "🐌"),
    (re_compile(r"posterdle #[\d-]+.*\n+ ⌛ .*\n 🍿.+🟩"), "📯"),
    (re_compile(r"posterdle #[\d-]+.*\n+ ⌛ 0️⃣ .*\n 🍿.+🟩"), "0️⃣"),
    (re_compile(r"posterdle #[\d-]+.*\n+ ⌛ .*\n 🍿 [⬜️🟥⬛️ ]+$"), "🐌"),
    (re_compile(r"namethatride #[\d-]+.*\n+ ⌛ .*\n 🚗.+🟩"), "🚙"),
    (re_compile(r"namethatride #[\d-]+.*\n+ ⌛ .*\n 🚗 [⬜️🟥⬛️ ]+$"), "🐌"),
    (re_compile(r"heardle #\d+.*\n+.*🟩"), "👂"),
    (re_compile(r"heardle #\d+.*\n+🔇"), "🐌"),
    (re_compile(r"flaggle .*\n+.*\d+ pts"), "⛳"),
    (re_compile(r"flaggle .*\n+.*gave up"), "🐌"),
    (re_compile(r"#Polygonle \d+ [1-6]/6[^🟧]+?🟩"), "🔷"),
    (re_compile(r"#Polygonle \d+ [1-6]/6[^🟩]+?🟧"), "🔶"),
    (re_compile(r"#Polygonle \d+ X/6"), "🐌"),
    (re_compile(r"#GuessTheGame #\d+.*\n+.*🎮[🟥⬛🟨 ]*🟩"), "🎮"),
    (re_compile(r"#GuessTheGame #\d+.*\n+.*🎮 [🟥⬛🟨 ]+$"), "🐌"),
    (re_compile(r"https://squaredle\.app/ \d+/\d+:"), "🟩"),
    (re_compile(r"https://squaredle\.app/ .*[^📖]*📖"), "📖"),
    (re_compile(r"https://squaredle\.app/ .*[^⏱️]*⏱️"), "⏱️"),
    (re_compile(r"https://squaredle\.app/ .*[^🎯]*🎯"), "🎯"),
    (re_compile(r"https://squaredle\.app/ .*[^🔥]*🔥"), "🔥"),
    (re_compile(r"Episode #\d+\n+📺 .*🟩"), "📺"),
    (re_compile(r"Episode #\d+\n+📺 [^🟩]+$"), "🐌"),
    (re_compile(r"Birdle #\d+ \d/5"), "🐦"),
]


class NotInGuildError(Exception):
    def __init__(self) -> None:
        super().__init__("Interaction is not in a guild, consider @guild_only")


class WordleReact(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        for pattern, emoji in reactions:
            if pattern.search(message.content):
                await message.add_reaction(emoji)
