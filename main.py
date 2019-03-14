# BUILTIN
import asyncio
import itertools
import os
import random
import sys
import traceback
# PIP
import discord
from discord.ext import commands
# CUSTOM
import config
from utils import utils

startup_extensions = [f'cogs.{os.path.splitext(file)[0]}'
                      for file in os.listdir('./cogs')
                      if file.endswith('.py')]  # Prevent errors for __pycache__
startup_extensions.append('jishaku')

prefixes = ['chloe', 'cp']
# Prefixes with spaces need to be at the very left
prefixes = [f'{p} ' for p in prefixes] + prefixes
prefixes += [p.title() for p in prefixes]
bot = commands.Bot(command_prefix=prefixes, case_insensitive=True)
bot.remove_command('help')


@bot.event
async def on_ready():
    output = '# Chloe bot is ready! #'
    print('\n' + '#' * len(output))
    print(output)
    print('#' * len(output))


@bot.check
async def is_ready(ctx):
    """
    Check to see if the bot is ready
    (internal cache can be used).
    """
    return bot.is_ready()


@bot.check
async def is_dms(ctx):
    """
    Do not allow any commands to be used in DMs.
    """
    if ctx.guild is None:
        raise commands.NoPrivateMessage(
            'Commands cannot be used in private messages.'
        )
        # return False
    return True


@bot.check
async def cmd_has_cd(ctx):
    """
    Assign a default CD to commands which where defined without one.
    """
    buckets = getattr(ctx.command, '_buckets')
    utils.assign_default_cooldown(buckets)
    return True


@bot.event
async def on_error(event, *args, **kwargs):
    """
    Handle errors unrelated to commands.
    """
    print(f'\nAn error unrelated to a command occurred:'
          f'\n{traceback.format_exc()}')


@bot.event
async def on_command_error(ctx, exc):
    """
    Print and report errors related to commands.
    """
    output_embed = await utils.get_bot_error(ctx, exc)

    if output_embed is not None:
        if isinstance(exc, commands.errors.CommandOnCooldown):
            # output_embed.title = discord.Embed.Empty
            # await ctx.send(embed=output_embed)
            cooldown = random.choice(['Chillax!', 'Chillax, sistah.'])
            cooldown += f' Try again in {round(exc.retry_after, 2)} seconds.'
            await ctx.send(cooldown)
        else:
            ai = await bot.application_info()
            await ai.owner.send(embed=output_embed)

    print_output = await utils.get_logging_error(ctx, exc)
    if print_output is None:
        return

    print(print_output + '\n')
    dev_error_channel = bot.get_channel(config.dev_error_channel_id)
    await dev_error_channel.send(f'```{print_output}```')

    traceback.print_exception(type(exc),
                              exc,
                              exc.__traceback__,
                              file=sys.stderr)


async def change_status():
    """
    Continuously change the bot's game status.
    """
    await bot.wait_until_ready()

    activity_types = [
        discord.Game(name='Prefixes are chloe and cp'),
        discord.Game(name='Use cphelp or cpabout'),
        discord.Activity(type=discord.ActivityType.listening,
                         name='Joyce complaining'),
        discord.Activity(type=discord.ActivityType.watching,
                         name='over the Junkyard'),
        discord.Activity(type=discord.ActivityType.watching,
                         name='Pompidou'),
        discord.Activity(type=discord.ActivityType.listening,
                         name="the Junkyard's wildlife"),
    ]
    activities = itertools.cycle(activity_types)

    while not bot.is_closed():
        current_activity = next(activities)
        await bot.change_presence(activity=current_activity)
        await asyncio.sleep(60)


if __name__ == '__main__':
    for extension in startup_extensions:
        try:
            bot.load_extension(extension)
        except discord.ClientException as err:
            exc = f'{type(err).__name__}: {err}'
            print(f'Failed to load extension {extension}\n{exc}')

    change_status_task = bot.loop.create_task(change_status())
    bot.run(config.TOKEN)
