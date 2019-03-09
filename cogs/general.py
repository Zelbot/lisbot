# PIP
import discord
from discord.ext import commands
# CUSTOM
import config
import utils


class General(commands.Cog):

    __slots__ = ('bot', )

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['board'])
    async def about(self, ctx):
        """
        Displays general information about the bot.
        """
        app_info = await self.bot.application_info()

        embed = discord.Embed(
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=config.butterfly_polaroid_url)
        embed.set_author(name=f'About {ctx.me.name}',
                         icon_url=utils.get_avatar_formatted(ctx.me))
        embed.add_field(name='Developer',
                        value=str(app_info.owner),
                        inline=True)
        embed.add_field(name='Need Help?',
                        value='Use cphelp',
                        inline=True)
        embed.add_field(name='Avatar Author',
                        value=f'[{config.avatar_author}]({config.avatar_author_link})',
                        inline=True)
        embed.add_field(name='Invite Link',
                        value=f'[Click here]({config.invite_link})',
                        inline=True)
        embed.set_image(url=config.junkyard_url)
        embed.set_footer(text='https://github.com/Zelbot')

        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(General(bot))
