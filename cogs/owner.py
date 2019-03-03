# BUILTIN
import asyncio
import re
import subprocess
import time
# PIP
import discord
from discord.ext import commands
# CUSTOM
from main import startup_extensions


class Owner(commands.Cog):

    __slots__ = ('bot', )

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return await ctx.bot.is_owner(ctx.author)

    async def cancel_custom_tasks(self):
        """
        Cancel all tasks that were created in main.py
        under `if __name__ == '__main__'`.
        """
        creation_point_re = re.compile(r'.+running at (.+):(\d+)')
        tasks = asyncio.Task.all_tasks(self.bot.loop)

        for t in tasks:
            coroname_and_file = t._repr_info()[1]
            mo = creation_point_re.match(coroname_and_file)
            if mo is None:
                continue

            file = mo.group(1)
            if file.endswith('/lis-bot/main.py'):
                t.cancel()

    @commands.command()
    async def restart(self, ctx):
        """
        Restarts the systemd service if on raspi.
        """
        try:
            await ctx.send('Restarting systemd service...')
            print('\nManually restarting lisbot systemd service')
            subprocess.Popen('sudo systemctl restart lisbot.service'.split())
        except FileNotFoundError:
            print('Cannot restart, not on Raspi')
            await ctx.send('The bot is currently not running on the Raspi!')

    @commands.command()
    async def reload(self, ctx):
        """
        Reloads all cogs.
        """
        await ctx.send('Reloading...')
        for extension_ in startup_extensions:
            try:
                self.bot.unload_extension(extension_)
                self.bot.load_extension(extension_)
            except discord.ClientException as err:
                exc = f'{type(err).__name__}: {err}'
                msg = f'Failed to load extension {extension_}\n{exc}'
                print(msg)
                await ctx.send(msg)
                return
        else:
            await ctx.send('Reloaded all cogs!')
            print('\n\n\nReloaded cogs, making space!\n\n\n')

    @commands.command(aliases=['kys', 'kysbot'])
    async def gooffline(self, ctx):
        """
        Closes the bot's connection and stops
        the systemd service on raspi (if on raspi).
        """
        output = 'Going offline, this could take a bit...'
        output += '\nI will, however, become unresponsive immediately!'
        await ctx.send(output)

        message = '# Cancelling all tasks and going offline! #'
        print(('\n' + '#' * len(message)))
        print(message)
        print(('#' * len(message)) + '\n')

        await self.cancel_custom_tasks()
        await asyncio.sleep(1)

        try:
            subprocess.Popen('sudo systemctl stop lisbot.service'.split())
        except FileNotFoundError:
            await self.bot.logout()

    @commands.command(aliases=['devdelete'])
    async def delete(self, ctx, message_id: int=None, channel_id: int=None):
        """
        Deletes the specified message.
        """
        if message_id is None:
            await ctx.send('You need to specify a message (and channel) ID!')
            return

        if channel_id is None:
            channel = ctx.channel
        else:
            channel = self.bot.get_channel(int(channel_id))
        message = await channel.get_message(int(message_id))

        try:
            await message.delete()
            if channel != ctx.channel:
                await ctx.send(f'Message on "{channel.guild}" #{channel}'
                               f' was successfully deleted!')
            else:
                # await ctx.message.add_reaction('LiSButterfly:546471168979369984')
                await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')
        except discord.Forbidden:
            await ctx.send("I'm forbidden from deleting that message!")

    @commands.command(aliases=['devstats'])
    async def stats(self, ctx):
        """
        Displays amounts of cogs/commands/guilds/users/emojis.
        """
        await ctx.send(
            f'{ctx.me.name} has **{len(self.bot.cogs)} cogs**'
            f'\n{ctx.me.name} has **{len(self.bot.commands)} cmds**'
            f'\n{ctx.me.name} is in **{len(self.bot.guilds)} servers**'
            f'\n{ctx.me.name} can see **{len(self.bot.users)} users**'
            f'\n{ctx.me.name} can access **{len(self.bot.emojis)} emojis**'
        )

    @commands.command()
    async def ping(self, ctx):
        """
        Calculates the ping time for one request.
        """
        start = time.perf_counter()
        await ctx.trigger_typing()  # Send a simple request
        end = time.perf_counter()
        time_delta = round((end - start) * 1000)
        await ctx.send(f'Pong! {time_delta}ms')

    @commands.command()
    async def devleave(self, guild_id: int=None):
        """
        Leaves a guild via ID.
        """
        if guild_id is None:
            return

        guild = await self.bot.get_guild(guild_id)
        await guild.leave()


def setup(bot):
    bot.add_cog(Owner(bot))
