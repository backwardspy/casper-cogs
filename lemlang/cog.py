from __future__ import annotations

import random
from pathlib import Path

import discord
from redbot.core import Config, app_commands, commands

words_path = Path(__file__).parent.resolve() / "data/oxford3k.txt"


class Lemlang(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, identifier=89226147595173940821)
        self.config.register_guild(channel_id=None, dictionary={})
        self.words = words_path.read_text().splitlines()

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        channel_id = await self.config.guild(message.guild).channel_id()
        if message.channel.id != channel_id:
            return

        if isinstance(message.author, discord.Member):
            author = message.author.nick or message.author.name
        else:
            author = message.author.name

        content = message.content

        dictionary = await self.config.guild(message.guild).dictionary()

        possible_replacements: set[str] = set()
        for word in content.split():
            if word.casefold() in dictionary:
                content = content.replace(word, dictionary[word.casefold()])
            elif word in self.words:
                possible_replacements.add(word.casefold())

        word: str | None = None
        translation: str | None = None
        if possible_replacements:
            word = random.choice(list(possible_replacements))
            translation = random.choice(self.words)
            dictionary[word] = translation
            content = content.replace(word, translation)
        await self.config.guild(message.guild).dictionary.set(dictionary)

        await message.delete()
        await message.channel.send(f"<{author}> {content}")

        if word:
            await message.channel.send(
                f'*"{word}" is now translated to "{translation}"!*',
            )

    @app_commands.command(name="lemlang-reset")
    async def reset_dictionary(self, interaction: discord.Interaction) -> None:
        await self.config.guild(interaction.guild).dictionary.set({})
        await interaction.response.send_message("Dictionary reset!")

    @app_commands.command(name="lemlang-channel")
    @app_commands.default_permissions(administrator=True)
    async def set_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ) -> None:
        await self.config.guild(interaction.guild).channel_id.set(channel.id)
        await interaction.response.send_message(
            f"Set Lemlang channel to {channel.mention}",
        )
