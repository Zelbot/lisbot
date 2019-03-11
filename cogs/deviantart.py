# BUILTIN
import functools
import random
import urllib.error
# PIP
import deviantart
import deviantart.deviation
import discord
from discord.ext import commands
# CUSTOM
import config
import utils


class DeviantArt(commands.Cog):

    __slots__ = ('bot', 'search_limit', 'post_limit', 'da_client')

    def __init__(self, bot):
        self.bot = bot
        self.search_limit = 5  # How many times we look for images per command
        self.post_limit = 20  # How many images get returned per iteration
        self.da_client = deviantart.Api(config.da_client_id,
                                        config.da_client_secret)

    async def cog_command_error(self, ctx, exc):
        """
        Catch 401 Unauthorized HTTPErrors which occurs when
        the access token has become invalidated.
        If this is the case, the client is refreshed and the command
        will get reinvoked.
        """
        if hasattr(exc, 'original') and isinstance(exc.original, deviantart.api.DeviantartError):
            wrapped_err = exc.original.args[0]
            if isinstance(wrapped_err, urllib.error.HTTPError) and wrapped_err.code == 401:
                await ctx.channel.trigger_typing()
                await self.refresh_client()
                await ctx.reinvoke()

    async def refresh_client(self):
        """
        The client's authorization is invalidated automatically
        after an hour, so we need to refresh it (just refreshing the
        access token using .refresh_token does not work).
        """
        self.da_client = deviantart.Api(config.da_client_id,
                                        config.da_client_secret)

    def da_req(self, endpoint, prep_deviations=False, **kwargs):
        """
        Wrapper for deviantart.Api._req to go around the limitations
        of the module's builtin functions like Api.browse
        """
        if not endpoint.startswith('/browse/'):
            endpoint = f'/browse/{endpoint}'

        res = self.da_client._req(endpoint, get_data=kwargs)

        if prep_deviations is False:
            return res

        # Copied from deviantart.api.py
        deviations = []

        for item in res['results']:
            d = deviantart.deviation.Deviation()
            d.from_dict(item)
            deviations.append(d)

        return {
            'results' : deviations,
            'has_more' : res['has_more'],
            'next_offset' : res['next_offset']
        }

    async def get_estimated_total(self, endpoint, query, **kwargs):
        """
        Get the maximum offset by firing off a request with
        an offset of 50000 (the allowed maximum in this module).
        The huge offset is just to ensure that the request is more
        likely to return sooner, as there is a high chance
        of no posts being found.
        """
        kwargs['offset'] = 50000
        if endpoint == 'tags':
            kwargs['tag'] = query
        else:
            kwargs['q'] = query

        partial = functools.partial(self.da_req, f'/browse/{endpoint}', **kwargs)
        res = await self.bot.loop.run_in_executor(None, partial)
        return res['estimated_total']

    async def choose_random_offset(self, num):
        """
        Choose a random offset by multiplying the
        search_limit and post_limit by one another
        and then subtracting that from the given number.
        Returns 0 if the outcome would be negative.
        """
        min_difference = self.search_limit * self.post_limit
        max_allowed_offset = num - min_difference
        if max_allowed_offset < 0:
            return 0

        # Return any possible offset in steps dictated by the post_limit
        # i.e. range(0, 20, 5) -> random.choice([0, 5, 10, 15])
        return random.choice(range(0, max_allowed_offset, self.post_limit))

    async def browse_popular(self, query, timerange='alltime', limit=20, offset=0):
        """
        Wrapper to browse /popular deviations
        to keep the function call uniform.
        """
        partial = functools.partial(self.da_client.browse,
                                    endpoint='popular', timerange=timerange,
                                    limit=limit, offset=offset, q=query)
        return await self.bot.loop.run_in_executor(None, partial)

    async def browse_newest(self, query, limit=20, offset=0):
        """
        Wrapper to browse /newest deviations
        to keep the function call uniform.
        """
        partial = functools.partial(self.da_client.browse,
                                    endpoint='newest', limit=limit,
                                    offset=offset, q=query)
        return await self.bot.loop.run_in_executor(None, partial)

    async def search_deviations(self, ctx, browse_func, query, *args, **kwargs):
        """
        Function to search for deviations, used at the start of commands.
        """
        searching_msg = await ctx.send('Searching...')
        await ctx.channel.trigger_typing()

        if ctx.channel.is_nsfw() is True:
            get = 'nsfw'
        else:
            get = 'sfw'

        deviations = await self.gather_deviations(browse_func, query, get=get,
                                                  *args, **kwargs)
        if not deviations:  # Search returned an empty list
            await ctx.send('I attempted to search through up to'
                           f' {self.search_limit * self.post_limit} posts'
                           f' for {get.upper()} content,'
                           ' but could not find anything.')
            await searching_msg.delete()

            return None, None

        return searching_msg, deviations

    async def gather_deviations(self, browse_func, *args, **kwargs):
        """
        Execute the specified browse_* method as many
        times as specified by the search_limit attribute
        and return all deviations that passed the checks
        of the filter_deviations method.
        """
        deviations = []
        get = kwargs.pop('get')
        res = await browse_func(*args, **kwargs)

        for i in range(self.search_limit):
            deviations += await self.filter_deviations(res['results'], get=get)

            if res['has_more'] is False:
                break

            if i != self.search_limit - 1:  # Prevent unnecessary API call on last iteration
                if 'offset' in kwargs.keys():
                    kwargs['offset'] = res['next_offset']
                res = await browse_func(*args, **kwargs)

        return deviations

    async def post_random_deviation(self, ctx, searching_msg, deviations):
        """
        Post a deviation in embed form, randomly chosen
        from the list of the given deviations.
        """
        chosen_deviation = random.choice(deviations)
        embed = await self.embed_from_deviation(ctx, chosen_deviation)

        await ctx.send(embed=embed)
        await searching_msg.delete()

    @staticmethod
    async def filter_deviations(deviations, get='all'):
        """
        Filter a list of deviations returned by
        DeviantArt.Api().browse based on whether
        or not the content is flagged as mature.
        Also only return deviations whose content attribute
        is not None, as it is needed later on.
        """
        filtered = [d for d in deviations
                    if d.content is not None
                    and d.author.username not in config.da_blacklisted_authors]

        if get == 'all':
            return filtered
        if get == 'nsfw':
            return [d for d in filtered if d.is_mature is True]
        if get == 'sfw':
            return [d for d in filtered if d.is_mature is False]

        raise ValueError('Bad argument for parameter <get>')

    @staticmethod
    async def embed_from_deviation(ctx, deviation):
        """
        Create a small embed to display the deviation
        together with a name of the author and a link
        to the piece.
        """
        footer = (f'Dimensions: {deviation.content["width"]}'
                  f'x{deviation.content["height"]}'
                  f' - Safe search: enabled')
        if ctx.channel.is_nsfw() is True:
            footer.replace('enabled', 'disabled')

        embed = discord.Embed(
            color=discord.Color.green(),
            description=':frame_photo: **Credit:**'
                        f' [{deviation.author}]({deviation.url})'
        )
        embed.set_image(url=deviation.content['src'])
        embed.set_footer(text=footer)

        return embed

    @commands.group(aliases=['da'], invoke_without_command=True)
    async def deviantart(self, ctx, *, query: utils.LiSQuery=None):
        """
        Searches the specified term on DeviantArt.
        ##nl## This defaults to the
        popular section, but you may search through the latest
        new deviations as well.
        ##nl## Usage: `cp deviantart (newest) term`
        ##nl## Note that this relies on the author properly
        tagging their work. This means that sometimes unrelated
        results will come up, which is unavoidable.
        """
        if query is None:
            return

        ctx.command = self.bot.get_command('deviantart popular')
        await utils.invoke_with_checks(ctx, ctx.command, query=query)

    @deviantart.command(name='popular', aliases=['pop'], hidden=True)
    async def _deviantart_popular(self, ctx, *, query: utils.LiSQuery=None, timerange='alltime'):
        """
        Query a search and post the result
        for the /popular section.
        """
        if query is None:
            return

        max_offset = await self.get_estimated_total(ctx.command.name, query,
                                                    timerange=timerange)
        random_offset = await self.choose_random_offset(max_offset)

        searching_msg, deviations = await self.search_deviations(
            ctx, self.browse_popular, query,
            timerange=timerange, limit=self.post_limit, offset=random_offset
        )
        if deviations is None:
            return

        await self.post_random_deviation(ctx, searching_msg, deviations)

    @deviantart.command(name='newest', aliases=['new'], hidden=True)
    async def _deviantart_newest(self, ctx, *, query: utils.LiSQuery=None):
        """
        Query a search and post the result
        for the /newest section.
        """
        if query is None:
            return

        searching_msg, deviations = await self.search_deviations(
            ctx, self.browse_newest, query,
            limit=self.post_limit
        )
        if deviations is None:
            return

        await self.post_random_deviation(ctx, searching_msg, deviations)


def setup(bot):
    bot.add_cog(DeviantArt(bot))
