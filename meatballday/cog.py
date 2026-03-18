from __future__ import annotations

import asyncio
import itertools
import logging
from typing import Protocol

import discord
import pendulum
from redbot.core import Config, app_commands, commands

CHECK_TIME = pendulum.time(hour=9, minute=0)
MAX_SLEEP = pendulum.duration(hours=3)

MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def to_ordinal(n: int) -> str:
    if 11 <= n <= 13:  # noqa: PLR2004
        return f"{n}th"

    suffixes = ["th", "st", "nd", "rd", "th"]
    index = min(n % 10, 4)
    return f"{n}{suffixes[index]}"


class NotInGuildError(Exception):
    def __init__(self) -> None:
        super().__init__("Interaction is not in a guild, consider @guild_only")


class ValidationError(Exception): ...


class NotNumericError(ValidationError):
    def __init__(self, value: str) -> None:
        super().__init__(f"{value} is not a number")


class OutOfRangeError(ValidationError):
    def __init__(self, value: int, start: int, stop: int) -> None:
        super().__init__(f"{value} is out of range {start}-{stop}")


def get_month(value: str) -> int:
    try:
        month = int(value)
    except ValueError as ex:
        raise NotNumericError(value) from ex

    valid_months = range(1, 13)
    if month not in valid_months:
        raise OutOfRangeError(month, 1, 12)

    return month


def get_day(value: str) -> int:
    try:
        day = int(value)
    except ValueError as ex:
        raise NotNumericError(value) from ex

    valid_days = range(1, 32)
    if day not in valid_days:
        raise OutOfRangeError(day, 1, 31)

    return day


class MeatballSetCallback(Protocol):
    async def __call__(
        self,
        month: int,
        day: int,
        *,
        interaction: discord.Interaction,
    ) -> None: ...


class MeatballSetModal(discord.ui.Modal):
    month = discord.ui.TextInput(
        label="Month",
        placeholder="1 - 12",
        min_length=1,
        max_length=2,
    )

    day = discord.ui.TextInput(
        label="Day",
        placeholder="1 - 31",
        min_length=1,
        max_length=2,
    )

    def __init__(self, callback: MeatballSetCallback) -> None:
        self.callback = callback
        super().__init__(title="Meatball Day")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        month = get_month(self.month.value)
        day = get_day(self.day.value)
        await self.callback(month, day, interaction=interaction)


log = logging.getLogger("red.casper_cogs.meatball_day")


def ensure_member(interaction: discord.Interaction) -> discord.Member:
    if not isinstance(interaction.user, discord.Member):
        raise NotInGuildError
    return interaction.user


class MeatballDay(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

        self.config = Config.get_conf(
            self,
            identifier=16620991240612872080,
            force_registration=True,
        )

        self.config.register_guild(
            channel=None,
            role=None,
            custom_members={},
        )

        self.config.register_member(
            month=None,
            day=None,
        )

        self.task: asyncio.Task | None = None
        self.next_check: pendulum.DateTime | None = None

    def _set_next_check(self) -> None:
        self.next_check = pendulum.tomorrow().at(
            hour=CHECK_TIME.hour,
            minute=CHECK_TIME.minute,
        )

    async def cog_load(self) -> None:
        self._set_next_check()
        self.task = asyncio.create_task(self._check_meatball_day())

    async def cog_unload(self) -> None:
        if self.task is not None:
            self.task.cancel()
            self.task = None
            self.next_check = None

    @app_commands.command(name="meatball-get")
    @app_commands.guild_only()
    async def meatball_get(self, interaction: discord.Interaction) -> None:
        member = ensure_member(interaction)
        month = await self.config.member(member).month()
        day = await self.config.member(member).day()

        if month is None or day is None:
            await interaction.response.send_message(
                "You have not set your Meatball Day yet. "
                "Please use `/meatball set` to set it.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "Your Meatball Day is "
                f"{MONTH_NAMES[month - 1]} {to_ordinal(day)}. :calendar:",
                ephemeral=True,
            )

    @app_commands.command(name="meatball-set")
    @app_commands.guild_only()
    async def meatball_set(self, interaction: discord.Interaction) -> None:
        async def callback(
            month: int,
            day: int,
            *,
            interaction: discord.Interaction,
        ) -> None:
            member = ensure_member(interaction)
            await self.config.member(member).month.set(month)
            await self.config.member(member).day.set(day)
            await interaction.response.send_message(
                "I have set your Meatball Day to "
                f"{MONTH_NAMES[month - 1]} {to_ordinal(day)}! :calendar:",
                ephemeral=True,
            )

        try:
            await interaction.response.send_modal(MeatballSetModal(callback))
        except ValidationError as error:
            await interaction.response.send_message(f"{error}. Please try again.")

    @app_commands.command(name="meatball-forget")
    @app_commands.guild_only()
    async def meatball_forget(self, interaction: discord.Interaction) -> None:
        member = ensure_member(interaction)
        await self.config.member(member).clear()
        await interaction.response.send_message(
            "Your Meatball Day has been lost, like tears in rain. :magic_wand:",
            ephemeral=True,
        )

    def _resolve_display(
        self,
        guild: discord.Guild,
        identifier: str,
    ) -> str:
        try:
            member_id = int(identifier)
            member = guild.get_member(member_id)
            if member is not None:
                return member.mention
        except ValueError:
            pass
        return identifier

    @app_commands.command(name="meatball-next")
    @app_commands.checks.cooldown(rate=1, per=3600)
    @app_commands.guild_only()
    async def meatball_next(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            msg = "Interaction guild is None, use @guild_only"
            raise RuntimeError(msg)

        all_members = await self.config.all_members(interaction.guild)
        custom_members = await self.config.guild(interaction.guild).custom_members()

        if not all_members and not custom_members:
            await interaction.response.send_message(
                "Nobody has set their Meatball Day yet. "
                "You could be the first! Use `/meatball set` to get started.",
                ephemeral=True,
            )
            return

        years = [pendulum.today().year, pendulum.today().add(years=1).year]

        configs: list[tuple[str, int, int]] = []
        for member_id, config in all_members.items():
            if member := interaction.guild.get_member(member_id):
                configs.append((member.mention, config["month"], config["day"]))

        for name, config in custom_members.items():
            display = self._resolve_display(interaction.guild, name)
            configs.append((display, config["month"], config["day"]))

        all_member_dates = sorted(
            (
                (display, pendulum.date(year=year, month=month, day=day))
                for year, (display, month, day) in itertools.product(years, configs)
            ),
            key=lambda pair: pair[1],
        )
        display, date = next(
            (display, date) for display, date in all_member_dates if date.is_future()
        )

        await interaction.response.send_message(
            f"Next Meatball Day is for {display} "
            f"on {date.to_formatted_date_string()}! :eyes:",
        )

    @app_commands.command(name="meatball-role")
    @app_commands.describe(role="The role to assign on Meatball Day")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def meatball_role(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
    ) -> None:
        if interaction.guild is None:
            msg = "Interaction guild is None, use @guild_only"
            raise RuntimeError(msg)

        await self.config.guild(interaction.guild).role.set(role.id)
        await interaction.response.send_message(
            f"I have set the Meatball Day role to {role.mention}.",
        )

    @app_commands.command(name="meatball-channel")
    @app_commands.describe(channel="The channel to post in on Meatball Day")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def meatball_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ) -> None:
        if interaction.guild is None:
            msg = "Interaction guild is None, use @guild_only"
            raise RuntimeError(msg)

        await self.config.guild(interaction.guild).channel.set(channel.id)
        await interaction.response.send_message(
            f"I have set the Meatball Day channel to {channel.mention}.",
        )

    @app_commands.command(name="meatball-recheck")
    @app_commands.default_permissions(administrator=True)
    async def meatball_recheck(self, interaction: discord.Interaction) -> None:
        await self._update_meatball_roles()
        await interaction.response.send_message(
            "I have rechecked all members for Meatball Day.",
        )

    @app_commands.command(name="meatball-set-member")
    @app_commands.describe(
        member="The member (mention/ID) or arbitrary name to set the Meatball Day for",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def meatball_set_member(
        self,
        interaction: discord.Interaction,
        member: str,
    ) -> None:
        if interaction.guild is None:
            msg = "Interaction guild is None, use @guild_only"
            raise RuntimeError(msg)

        resolved_member = None
        try:
            member_id = int(member)
            resolved_member = interaction.guild.get_member(member_id)
        except ValueError:
            pass

        if resolved_member is None:
            for m in interaction.guild.members:
                if member in (m.name, m.display_name):
                    resolved_member = m
                    break

        async def callback(
            month: int,
            day: int,
            *,
            interaction: discord.Interaction,
        ) -> None:
            if resolved_member is not None:
                await self.config.member(resolved_member).month.set(month)
                await self.config.member(resolved_member).day.set(day)
                display = resolved_member.mention
            else:
                async with self.config.guild(
                    interaction.guild,
                ).custom_members() as custom:
                    custom[member] = {"month": month, "day": day}
                display = member
            await interaction.response.send_message(
                f"I have set {display}'s Meatball Day to "
                f"{MONTH_NAMES[month - 1]} {to_ordinal(day)}.",
            )

        try:
            await interaction.response.send_modal(MeatballSetModal(callback))
        except ValidationError as ex:
            await interaction.response.send_message(
                f"{ex}. Please try again.",
                ephemeral=True,
            )

    async def _check_meatball_day(self) -> None:
        if not self.bot.is_ready():
            log.debug("Waiting for bot to be ready")
            await self.bot.wait_until_ready()

        log.debug("Bot is ready, entering check loop")
        while True:
            if self.next_check is None:
                msg = "next_check is None"
                raise RuntimeError(msg)

            until_check = min(self.next_check - pendulum.now(), MAX_SLEEP)
            if until_check.in_seconds() > 0:
                log.info(
                    "Next check is at %s; sleeping for %s",
                    self.next_check,
                    until_check.in_words(),
                )
                await asyncio.sleep(until_check.in_seconds())
            else:
                log.info("Check time has elapsed, checking for meatball days now")

            await self._update_meatball_roles()

            self._set_next_check()
            await asyncio.sleep(1)

    async def _update_meatball_roles(self) -> None:
        all_meatball_days = await self.config.all_members()
        all_guilds = await self.config.all_guilds()
        guild_ids = set(all_meatball_days.keys()) | set(all_guilds.keys())

        for guild_id in guild_ids:
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                if guild_id in all_meatball_days:
                    log.warning(
                        "Guild %s no longer exists, removing from config.",
                        guild_id,
                    )
                    await self.config.guild_from_id(guild_id).clear()
                continue

            channel_id = await self.config.guild(guild).channel()
            channel = guild.get_channel(channel_id)
            if channel is None:
                log.warning(
                    "Channel %s does not exist in guild %s, skipping.",
                    channel_id,
                    guild,
                )
                continue

            if not isinstance(channel, discord.TextChannel):
                log.warning(
                    "Channel %s in guild %s is not a text channel, skipping.",
                    channel,
                    guild,
                )
                continue

            role_id = await self.config.guild(guild).role()
            role = guild.get_role(role_id)
            if role is None:
                log.warning(
                    "Role %s does not exist in guild %s, skipping.",
                    role_id,
                    guild,
                )
                continue

            members = all_meatball_days.get(guild_id, {})
            for member_id, meatball_day in members.items():
                member = guild.get_member(member_id)
                if member is None:
                    log.warning(
                        "Member %s no longer exists in guild %s, removing from config.",
                        member_id,
                        guild,
                    )
                    await self.config.member_from_ids(guild_id, member_id).clear()
                    continue

                today = pendulum.today()
                is_meatball_day = (
                    today.month == meatball_day["month"]
                    and today.day == meatball_day["day"]
                )

                if is_meatball_day and role not in member.roles:
                    await member.add_roles(role)
                    log.info(
                        "Added Meatball Day role to %s in guild %s",
                        member,
                        guild,
                    )

                    await channel.send(
                        f"It's {member.mention}'s Meatball Day! :partying_face::tada:",
                    )
                elif not is_meatball_day and role in member.roles:
                    await member.remove_roles(role)
                    log.info(
                        "Removed Meatball Day role from %s in guild %s",
                        member,
                        guild,
                    )

            async with self.config.guild(guild).custom_members() as custom_members:
                for name, meatball_day in custom_members.items():
                    today = pendulum.today()
                    is_meatball_day = (
                        today.month == meatball_day["month"]
                        and today.day == meatball_day["day"]
                    )

                    if is_meatball_day and not meatball_day.get("announced"):
                        meatball_day["announced"] = True
                        display = self._resolve_display(guild, name)
                        await channel.send(
                            f"It's {display}'s Meatball Day! :partying_face::tada:",
                        )
                    elif not is_meatball_day and meatball_day.get("announced"):
                        meatball_day["announced"] = False
