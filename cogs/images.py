# BUILTIN
import random
import string
import os
# PIP
import discord
from discord.ext import commands
# CUSTOM
from utils import utils


class Images(commands.Cog):

    __slots__ = ('bot', 'ip')

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """
        Check to see if the bot has the required permissions
        for some specific commands.
        """
        if ctx.command.name == 'image':
            if ctx.channel.permissions_for(ctx.me).attach_files is False:
                await ctx.send('I need `Attach Files` permissions to work properly!')
                return False

        if ctx.command.name in ['image', 'quote']:
            if ctx.channel.permissions_for(ctx.me).add_reactions is False:
                await ctx.send('I need `Add Reactions` permissions to work properly!')
                return False

        return True

    @staticmethod
    def generate_folder_url(base_folder):
        """
        Generate a source URL based on the folder name.
        """
        if base_folder.lower().startswith('reddit'):
            url = f'https://www.reddit.com/u/{base_folder.split("-")[1]}'
        elif base_folder.lower().startswith('steamcommunity'):
            url = f'https://steamcommunity.com/id/{base_folder.split("-")[1]}/'
        elif base_folder.lower().endswith(('tumblr.com', 'deviantart.com',
                                           'life-is-strange.wikia.com')):
            url = f'https://{base_folder}'
        else:
            url = f'https://www.{base_folder}'

        return url

    def get_sources_and_links(self):
        """
        Map generated URLs to the name of the folder which they're saved in.
        Note that the images are located in another project's structure
        so we have to go with that project's path here (images_path)
        """
        images_path = os.path.join(os.path.abspath('../zelbot/'),
                                   'images', 'Life_is_Strange')
        all_folders = [os.path.relpath(os.path.join(images_path, folder))
                       for folder in os.listdir(images_path)]

        urls = {}
        for folder in all_folders:
            url = self.generate_folder_url(os.path.basename(folder))
            urls[url] = folder

        return urls

    def choose_image_folder(self, args):
        """
        Chooses a folder to use in the image command.
        """
        urls = self.get_sources_and_links()

        if len(args) == 1 and args[0].lower() == 'random':
            # return random.choice(list(urls.keys()))
            return random.choice(list(urls.values()))

        # Remove args that do not contain letters or numbers
        # to prevent matching things like singular periods
        alnum_args = [arg for arg in args
                      if any(letter in string.ascii_letters for letter in arg)
                      or any(letter in '0123456789' for letter in arg)]

        # Match based on URL instead of folder name
        matched_urls = [url for url in urls
                        if any(arg.lower() in url.lower()
                               for arg in alnum_args)]
        if matched_urls:
            chosen_url = random.choice(matched_urls)
            chosen_folder = urls[chosen_url]
            return chosen_folder
        return None

    @commands.command(aliases=['img', 'picture', 'pic'])
    async def image(self, ctx, *args):
        """
        Posts an image about Life is Strange, supports matching based on sources.
        ##nl## Use `cp image` to get an overview of all available sources.
        ##nl## Use `cp image random` to get a random image.
        """
        if not args:
            source_paginator = utils.OverviewPaginator(self.bot, ctx, self)
            await source_paginator.prep_image_source_paginator()
            await source_paginator.paginate()
            return

        chosen_folder = self.choose_image_folder(args)
        if chosen_folder is None:
            await ctx.send(f'Could not match a source based on `{" ".join(args)}`!')
            return

        chosen_pic = os.path.join(chosen_folder, random.choice(os.listdir(chosen_folder)))
        pic_base = os.path.basename(chosen_pic)
        author_url = self.generate_folder_url(os.path.basename(chosen_folder))

        upload_message = await ctx.send('Uploading...')

        # From `?tag localembed` on the discord.py Discord server
        file = discord.File(chosen_pic,
                            filename=pic_base)
        embed = discord.Embed(color=discord.Color.blue(),
                              description=(':frame_photo: **Credit:**'
                                           f' [{author_url}]({author_url})'))
        embed.set_image(url=f'attachment://{pic_base}')

        async with ctx.channel.typing():
            await ctx.send(file=file, embed=embed)

        await upload_message.delete()


def setup(bot):
    bot.add_cog(Images(bot))
