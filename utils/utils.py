# PIP
import discord
from discord.ext import commands


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
        discord.NotFound
    ]
    # Make the owner exempt from cooldowns
    if isinstance(exc, commands.errors.CommandOnCooldown):
        if await ctx.bot.is_owner(ctx.author) is True:
            # Reinvoking `jsk su` commands here means their exceptions
            # would not be handled by on_command_error
            if ctx.command != ctx.bot.get_command('jsk su'):
                await ctx.reinvoke()
                return

    if type(exc) in ignored_exception_types:
        return None

    error_embed = discord.Embed(
        # title=f':x: A {type(exception).__name__} error occurred',
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
        commands.errors.TooManyArguments
    ]
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
