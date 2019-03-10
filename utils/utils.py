# BUILTIN
import asyncio
import types
import urllib.error
# PIP
import discord
from discord.ext import commands


class OverviewPaginator:
    """
    Paginator to make the image sources output more readable.
    """
    __slots__ = ('bot', 'ctx', 'cog', 'paginator', 'index')

    def __init__(self, bot, ctx, cog):
        self.bot = bot
        self.ctx = ctx
        self.cog = cog
        self.paginator = commands.Paginator()
        self.index = 0

    async def await_pagination_reaction(self, message):
        """
        Enable reactions so that a user can flip between pages
        of a cog's command help overview.
        """
        await message.add_reaction('⬅')
        await message.add_reaction('➡')

        def check(reaction_, user_):
            return user_.id == self.ctx.author.id \
                   and str(reaction_) in ['➡', '⬅'] \
                   and reaction_.message.id == message.id

        try:
            reaction, user = await self.bot.wait_for('reaction_add',
                                                     timeout=30.0,
                                                     check=check)
        except asyncio.TimeoutError:
            try:
                await message.clear_reactions()
            except discord.NotFound:
                return
            except discord.Forbidden:
                await message.remove_reaction('⬅', self.ctx.me)
                await message.remove_reaction('➡', self.ctx.me)
        else:
            index_before = self.index
            if str(reaction) == '➡' and self.index < len(self.paginator.pages) - 1:
                self.index += 1
            elif str(reaction) == '⬅' and self.index > 0:
                self.index -= 1

            if index_before != self.index:
                try:
                    await message.edit(content=self.paginator.pages[self.index])
                except discord.NotFound:
                    return
                if self.ctx.channel.permissions_for(self.ctx.me).manage_messages is True:
                    await message.remove_reaction(reaction, user)
            # Reset timer, wait for next pagination reaction
            await self.await_pagination_reaction(message)

    async def prep_image_source_paginator(self):
        """
        Prepare a paginator for the sources of the image command.
        """
        urls = self.cog.get_sources_and_links()
        paginator = commands.Paginator(prefix='**Available sources:**',
                                       suffix='')

        for index, url in enumerate(urls.keys()):
            # Close each page when it has reached 3 commands
            if index % 15 == 0 and index > 0:
                paginator.close_page()
            paginator.add_line(f'  <{url}>')

        self.paginator = paginator

    async def prep_quote_char_paginator(self):
        """
        Prepare a paginator for the character overview of the quote command.
        """
        single_chars = self.cog.get_single_char_overview()
        char_pairs = self.cog.get_char_pair_overview()
        paginator = commands.Paginator(prefix=f'```css\n[Available Characters]\n```',
                                       suffix='')

        for overview in [single_chars, char_pairs]:
            paginator.add_line('```ml')

            for line in overview.split('\n'):
                paginator.add_line(line)

            paginator.add_line('```')
            paginator.close_page()

        self.paginator = paginator

    async def paginate(self):
        """
        Cycle through multiple pages using reactions.
        """
        page = await self.ctx.send(self.paginator.pages[0])
        if len(self.paginator.pages) > 1:
            await self.await_pagination_reaction(page)


class QuoteChar(commands.Converter):
    """
    Converter to more easily keep the names of quote characters uniform.
    """
    @staticmethod
    async def format_name(name):
        """
        Used to keep the format of quote characters names uniform.
        """
        return name.lower().title().replace('And', '&')

    async def convert(self, ctx, argument):
        if not isinstance(argument, str):
            raise ValueError(f'Passed type {type(argument).__name__} '
                             f'for argument "{argument}", expected type str')

        return await self.format_name(argument)


class LiSQuery(commands.Converter):
    """
    Convert a DeviantArt search query to guarantee
    a result about Life is Strange
    """
    @staticmethod
    async def format_query(query):
        """
        Replace 'lis' with 'lifeisstrange'
        or put into the query if not already present.
        """
        query = ' '.join(query.split())  # Get rid of newlines
        query = query.lower()

        if 'lis' in query:
            query = query.replace('lis', 'lifeisstrange')
        elif 'lifeisstrange' not in query:
            query = f'{query} lifeisstrange'

        return query

    async def convert(self, ctx, argument):
        if not isinstance(argument, str):
            raise ValueError(f'Passed type {type(argument).__name__} '
                             f'for argument "{argument}", expected type str')

        return await self.format_query(argument)


def get_role_color(member):
    """
    Check to see if the member's role color is the default
    and adjust to dark theme accordingly.
    Then return color hex, color object and color rgb tuple.
    """
    if str(member.color) == '#000000':
        color_hex = '#ffffff'
        color_obj = discord.Color(int(color_hex[1:], 16))
        color_rgb = color_obj.to_rgb()
        return color_hex, color_obj, color_rgb

    return str(member.color), member.color, member.color.to_rgb()


def assign_default_cooldown(buckets):
    """
    Assigns a default cooldown to a command which was defined without one.
    """
    if buckets._cooldown is None:  # Command was defined without a cooldown
        buckets._cooldown = commands.Cooldown(1,  # Can invoke command once
                                              10.0,  # Every ten seconds
                                              commands.BucketType.user)


async def get_bot_error(ctx, exc):
    """
    Prepare bot output for command errors.
    """
    ignored_exception_types = [
        commands.errors.MissingPermissions,
        commands.errors.CommandNotFound,
        commands.errors.CheckFailure,
        commands.errors.BadArgument,
        commands.NotOwner,
        discord.NotFound,
        discord.errors.Forbidden
    ]
    # Make the owner exempt from cooldowns
    if isinstance(exc, commands.errors.CommandOnCooldown):
        if await ctx.bot.is_owner(ctx.author) is True:
            # Reinvoking `jsk su` commands here means their exceptions
            # would not be handled by on_command_error
            if ctx.command != ctx.bot.get_command('jsk su'):
                await ctx.reinvoke()
                return

    # Ignore 401 HTTPErrors caused by the DA API access token expiring
    if isinstance(exc, commands.errors.CommandInvokeError):
        wrapped_err = exc.original.args[0]
        if isinstance(wrapped_err, urllib.error.HTTPError) and wrapped_err.code == 401:
            return None

    if type(exc) in ignored_exception_types:
        return None

    error_embed = discord.Embed(
        # title=f':x: A {type(exc).__name__} error occurred',
        color=get_role_color(ctx.me)[1],
        description=(str(exc))
    )

    return error_embed


async def get_logging_error(ctx, exc):
    """
    Prepare logging output for command errors.
    """
    guild = ctx.guild
    channel = ctx.channel
    author = ctx.author
    content = ctx.message.content

    # Avoid logging some errors
    ignored_exception_types = [
        commands.errors.CommandNotFound,
        commands.errors.MissingPermissions,
        commands.errors.BotMissingPermissions,
        commands.errors.CheckFailure,
        commands.errors.NoPrivateMessage,
        commands.errors.BadArgument,
        commands.errors.CommandOnCooldown,
        commands.errors.MissingRequiredArgument,
        commands.errors.TooManyArguments,
        discord.NotFound,
        discord.errors.Forbidden
    ]
    # Ignore 401 HTTPErrors caused by the DA API access token expiring
    if isinstance(exc, commands.errors.CommandInvokeError):
        wrapped_err = exc.original.args[0]
        if isinstance(wrapped_err, urllib.error.HTTPError) and wrapped_err.code == 401:
            return None

    if type(exc) in ignored_exception_types:
        return None

    # Report errors to a specific channel as terminal is mostly unavailable
    full_error_output = (f'An error occurred on "{guild}" / #{channel}:'
                         f'\n{exc}'
                         f'\n\nMessage by {author} - {author.id}:\n{content}')
    return full_error_output


def get_avatar_formatted(user):
    """
    Get an avatar of a User (or Member) in either .PNG
    or .GIF format, depending on whether or not it is animated.
    """
    if user.is_avatar_animated() is True:
        return user.avatar_url_as(format='gif')
    return user.avatar_url_as(format='png')


async def invoke_with_checks(ctx, command, *args, **kwargs):
    """
    Execute the specified command only if all checks pass.
    """
    if type(command) not in [types.FunctionType, types.MethodType, commands.Command, str]:
        raise ValueError(f'Argument for parameter <command> is invalid.')

    if type(command) in [types.FunctionType, types.MethodType]:
        command = ctx.bot.get_command(command.__name__)

    if type(command) == str:
        command = ctx.bot.get_command(command)

    if await command.can_run(ctx) is True:
        await ctx.invoke(command, *args, **kwargs)
