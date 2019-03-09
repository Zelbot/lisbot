import random
import deviantart
import discord
from discord.ext import commands
import config

da_client = deviantart.Api(config.da_client_id, config.da_client_secret)


class DeviantArt(commands.Cog):

    __slots__ = ('bot', 'search_limit', 'post_limit')

    def __init__(self, bot):
        self.bot = bot
        self.search_limit = 5  # How many times we look for images per command
        self.post_limit = 20  # How many images get returned per iteration

    async def cog_check(self, ctx):
        return await ctx.bot.is_owner(ctx.author)

    @staticmethod
    async def get_max_offset(endpoint, query):
        """
        Get the maximum offset by firing off a request with
        an offset of 50000 (the allowed maximum in this module).
        The huge offset is just to ensure that the request is more
        likely to return sooner, as there is a high chance
        of no posts being found.
        """
        get_data = {'offset': 50000}
        if endpoint == 'tags':
            get_data['tag'] = query
        else:
            get_data['q'] = query

        res = da_client._req(f'/browse/{endpoint}', get_data=get_data)
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

    @staticmethod
    async def browse_popular(query, timerange='alltime', limit=20, offset=0):
        """
        Wrapper to browse /popular deviations
        to keep the function call uniform.
        """
        return da_client.browse(endpoint='popular', timerange=timerange,
                                limit=limit, offset=offset, q=query)

    @staticmethod
    async def browse_newest(query, limit=20, offset=0):
        """
        Wrapper to browse /newest deviations
        to keep the function call uniform.
        """
        return da_client.browse(endpoint='newest', limit=limit,
                                offset=offset, q=query)

    @staticmethod
    async def browse_tags(tag, limit=20, offset=0):
        """
        Wrapper to browse DeviantArt /tags
        to keep the function call uniform.
        """
        return da_client.browse(endpoint='tags', limit=limit,
                                offset=offset, tag=tag)

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
            await ctx.send(f'I searched through {self.search_limit * self.post_limit}'
                           f' {get.upper()}-only posts,'
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
        get = kwargs.pop('get')
        deviations = []
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
        is not None, as we need the content's source
        and dimensions.
        """
        if get == 'all':
            return [d for d in deviations if d.content is not None]

        if get == 'nsfw':
            return [d for d in deviations if d.content is not None
                                          and d.is_mature is True]

        if get == 'sfw':
            return [d for d in deviations if d.content is not None
                                          and d.is_mature is False]

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
    async def deviantart(self, ctx, tag):
        """
        Searches through various sections of DeviantArt.
        ##nl## Available sections are: `popular`, `newest`, `tag`
        ##nl## Usage: `cp deviantart section term`, i.e.
        `cp deviantart tag lis`
        ##nl## If no section is specified, this defaults to tag.
        ##nl## Note that the search for `tags` can only ever be one word.
        This does not apply to the popular and newest search.
        """
        ctx.command = self.bot.get_command('deviantart tags')
        await ctx.invoke(ctx.command, tag)

    @deviantart.command(name='popular', aliases=['pop'], hidden=True)
    async def _deviantart_popular(self, ctx, *, query):
        """
        Query a search and post the result
        for the /popular section.
        """
        max_offset = await self.get_max_offset(ctx.command.name, query)
        random_offset = await self.choose_random_offset(max_offset)

        searching_msg, deviations = await self.search_deviations(
            ctx, self.browse_popular, query,
            timerange='alltime', limit=self.post_limit, offset=random_offset
        )
        if deviations is None:
            return

        await self.post_random_deviation(ctx, searching_msg, deviations)

    @deviantart.command(name='newest', aliases=['new'], hidden=True)
    async def _deviantart_newest(self, ctx, *, query):
        """
        Query a search and post the result
        for the /newest section.
        """
        searching_msg, deviations = await self.search_deviations(
            ctx, self.browse_newest, ctx.command.name, query,
            limit=self.post_limit
        )
        if deviations is None:
            return

        await self.post_random_deviation(ctx, searching_msg, deviations)

    @deviantart.command(name='tags', aliases=['tag'], hidden=True)
    async def _deviantart_tags(self, ctx, tag):
        """
        Query a search and post the result
        for the /tags section.
        """
        max_offset = await self.get_max_offset(ctx.command.name, tag)
        random_offset = await self.choose_random_offset(max_offset)

        searching_msg, deviations = await self.search_deviations(
            ctx, self.browse_tags, tag,
            limit=self.post_limit, offset=random_offset
        )
        if deviations is None:
            return

        await self.post_random_deviation(ctx, searching_msg, deviations)


def setup(bot):
    bot.add_cog(DeviantArt(bot))
