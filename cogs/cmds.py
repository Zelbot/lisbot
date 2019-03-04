# BUILTIN
import asyncio
import os
import random
import string
# PIP
import discord
from discord.ext import commands
from numpy.random import choice
# CUSTOM
import config
from utils import utils
from data.quotes import quotes


class OverviewPaginator:
    """
    Paginator to make the image sources output more readable.
    """
    __slots__ = ('bot', 'ctx', 'cmds', 'paginator', 'index')

    def __init__(self, bot, ctx, cmds):
        self.bot = bot
        self.ctx = ctx
        self.cmds = cmds
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
        urls = self.cmds.get_sources_and_links()
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
        single_chars = self.cmds.get_single_char_overview(quotes)
        char_pairs = self.cmds.get_char_pair_overview(quotes)
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


class CMDS(commands.Cog):
    """
    The main cog to host this bot's commands.
    """
    __slots__ = ('bot', )

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def generate_folder_url(base_folder):
        """
        Generate source URL based on the folder name.
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
        freecam_path = os.path.join(os.getcwd(), 'images', 'Life_is_Strange')
        all_folders = [os.path.relpath(os.path.join(freecam_path, folder))
                       for folder in os.listdir(freecam_path)]

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
        if args:
            if len(args) == 1 and args[0].lower() == 'random':
                return urls[random.choice(list(urls.keys()))]

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

    @staticmethod
    def apply_ini_markdown(quote):
        """
        Encloses character names from dialogue pairs in square brackets
        and adds ini markdown to highlight them
        """
        lines = quote.split('\n')
        for index, line in enumerate(lines[:]):
            character = line.split(':')[0]
            sentence = ' '.join(line.split(':')[1:])
            lines[index] = f'[{character}]:{sentence}'

        quote_with_ini = 'ini\n' + '\n'.join(lines)
        return quote_with_ini


    def get_quote_char_overview(self, quotes_dict, title):
        """
        Displays an overview of the available characters
        for the quotes command, formatted a little nicer
        """
        # Construct an overview string using markdown to color the text
        # overview = f'```prolog\n{title}```\n'
        overview = f'```css\n[{title}]```\n'
        overview += '```ml\n'
        overview += self.get_single_char_overview(quotes_dict) + '\n\n'
        overview += self.get_char_pair_overview(quotes_dict) + '\n```'
        return overview

    @staticmethod
    def get_single_char_overview(quotes_dict):
        """
        Prepares an overview of all single characters
        from the specified quotes dict
        """
        single_chars = sorted([char for char in quotes_dict if '&' not in char])
        quotes_lens = [str(len(quotes_dict[char])) for char in single_chars]
        longest_quote = len(max(quotes_lens, key=len))

        left_names = []
        right_names = []
        for index, item in enumerate(single_chars):
            if index % 2 == 0:
                left_names.append(item)
            else:
                right_names.append(item)

        # Add padding and quote count
        for name_list in [left_names, right_names]:
            longest_str = len(max(name_list, key=len))

            for index, name in enumerate(name_list[:]):
                padded_name = name.ljust(longest_str) + '  -  '
                padded_count = str(len(quotes_dict[name])).rjust(longest_quote)
                name_list[index] = padded_name + padded_count

            # Add padding and "quote" or "quotes"
            longest_str = len(max(name_list, key=len))
            for index, name in enumerate(name_list[:]):
                char_name = name.split('-')[0].strip()
                padded_str = name.ljust(longest_str + 1)

                if len(quotes_dict[char_name]) == 1:
                    padded_str += 'quote'
                else:
                    padded_str += 'quotes'

                name_list[index] = padded_str

        # Add padding in-between names
        for index, name in enumerate(left_names[:]):
            left_names[index] = name.ljust(len(max(left_names)) + 3)

        # Build overview in the format of "Char1 - N quotes   Char2 - N quotes"
        overview = ''
        for index, name in enumerate(left_names):
            try:
                overview += left_names[index] + right_names[index] + '\n'
            except IndexError:
                # Can't build pair bc left_names has one more char
                overview += left_names[index] + '\n'

        return overview.strip()

    @staticmethod
    def get_char_pair_overview(quotes_dict):
        """
        Prepares an overview of all dialogue pairs
        from the specified quotes dict
        """
        char_pairs = sorted([char for char in quotes_dict if '&' in char])
        quotes_lens = [str(len(quotes_dict[char])) for char in char_pairs]
        longest_quote = len(max(quotes_lens, key=len))

        firsts_of_pairs = []
        seconds_of_pairs = []
        for pair in char_pairs:
            first_char, second_char = pair.split('&')
            firsts_of_pairs.append(first_char.strip())
            seconds_of_pairs.append(second_char.strip())

        # Add padding and ampersand
        longest_str = len(max(firsts_of_pairs, key=len))
        for index, name in enumerate(firsts_of_pairs[:]):
            firsts_of_pairs[index] = name.ljust(longest_str) + '  &  '

        # Add padding and quote count
        longest_str = len(max(seconds_of_pairs, key=len))
        for index, name in enumerate(seconds_of_pairs[:]):
            padded_name = name.ljust(longest_str) + '  -  '
            pair = char_pairs[index]
            padded_count = str(len(quotes_dict[pair])).rjust(longest_quote)
            seconds_of_pairs[index] = padded_name + padded_count

        # Add padding and "quote" or "quotes"
        longest_str = len(max(seconds_of_pairs, key=len))
        for index, name in enumerate(seconds_of_pairs[:]):
            pair = char_pairs[index]
            padded_str = name.ljust(longest_str + 1)

            if len(quotes_dict[pair]) == 1:
                padded_str += 'quote'
            else:
                padded_str += 'quotes'

            seconds_of_pairs[index] = padded_str

        # Build overview in the format of "Joyce Price & Chloe Price - N quotes"
        overview = ''
        for index, name in enumerate(firsts_of_pairs):
            overview += firsts_of_pairs[index] + seconds_of_pairs[index] + '\n'

        return overview.strip()

    @staticmethod
    def get_quote_chars(char, quotes_dict):
        """
        Prepare a list of all matched characters for the quote commands
        """
        if char.count('&') > 1:  # Only two people per pair allowed, ever
            return None

        if char.lower() == 'random':
            available_chars = list(quotes_dict.keys())

        elif char in quotes_dict:
            available_chars = [name for name in quotes_dict.keys()
                               if char in name]

        # char not in quotes_dict
        # Incomplete name, e.g. 'Max' instead of 'Max Caulfield'
        # Side effect: 'D' also chooses a character, i.e. 'Daniel Da Costa'
        elif '&' in char:
            # Complete dialogue pairs like 'William Price & Chloe Price'
            if not char.endswith('&'):
                name1 = char.split('&')[0].strip()
                name2 = char.split('&')[1].strip()

                available_chars = [name for name in quotes_dict.keys()
                                   if name1 in name and name2 in name
                                   and '&' in name]
                # Remove unwanted dialogue pairs in case of double names
                # e.g. removes 'Rachel Amber & Chloe Price' etc. for 'z!quote price and price'
                available_chars = [name for name in available_chars
                                   if (name1 in name.split('&')[0] and name2 in name.split('&')[1])
                                   or (name1 in name.split('&')[1] and name2 in name.split('&')[0])]
            # Incomplete dialogue pairs like 'Max Caulfield &'
            else:
                char_name = char.split('&')[0].strip()
                available_chars = [name for name in quotes_dict.keys()
                                   if '&' in name and char_name in name]

        # Any matches based on both first and last name
        else:
            available_chars = [name for name in quotes_dict.keys()
                               # if any(split.startswith(char) for split in name.split())]
                               if any(split_.startswith(tuple(char.split()))
                                      for split_ in name.split())]

        # Can be an empty list of no match was found
        return available_chars

    @staticmethod
    def choose_quote_char(characters, quotes_dict, weighted=False):
        """
        Chooses a character name to be used in the quotes command.
        If weighted is True, the amount of quotes for each character
        is taken into account when the choice is made.
        """
        if not characters:
            return None
        if weighted is False:
            return random.choice(characters)

        chars = {name: list_ for name, list_ in quotes_dict.items()
                 if name in characters}
        # Calculate a list of percentage-wise probabilities by dividing
        # the length of a single list through the sum of all lengths of all lists
        probabilities = [len(list_) / sum([len(l) for l in chars.values()])
                         for list_ in chars.values()]
        return choice(a=list(chars.keys()), p=probabilities)

    @commands.command(aliases=['img', 'picture', 'pic'])
    async def image(self, ctx, *args):
        """
        Posts an image about Life is Strange, supports matching based on sources.
        ##nl## Use `cp image` to get an overview of all available sources.
        ##nl## Use `cp image random` to get a random image.
        """
        if not args:
            source_paginator = OverviewPaginator(self.bot, ctx, self)
            await source_paginator.prep_image_source_paginator()
            await source_paginator.paginate()
            return

        chosen_folder = self.choose_image_folder(args)
        if chosen_folder is None:
            await ctx.send(f'Could not match a source based on `{" ".join(args)}`!')
            return

        chosen_folder = self.choose_image_folder(args)
        chosen_pic = os.path.join(chosen_folder, random.choice(os.listdir(chosen_folder)))
        pic_base = os.path.basename(chosen_pic)
        author_url = self.generate_folder_url(os.path.basename(chosen_folder))

        upload_message = await ctx.send('Uploading...')

        # From `?tag localembed` on the discord.py Discord server
        file = discord.File(chosen_pic,
                            filename=pic_base)
        # Add markdown for the URL in the description so the URL
        # stays clickable if the embed gets mocked
        embed = discord.Embed(color=discord.Color.blue(),
                              description=(':frame_photo: **Credit:**'
                                           f' [{author_url}]({author_url})'))
        embed.set_image(url=f'attachment://{pic_base}')

        async with ctx.channel.typing():
            await ctx.send(file=file, embed=embed)

        await upload_message.delete()

    # @image.before_invoke
    # async def before_image(self, ctx):
    #     """
    #     Images are in the zelbot directory, so we cd there.
    #     """
    #     if ctx.args[2:]:  # Source was specified
    #         if os.path.basename(os.getcwd()) != 'lis-bot':
    #             os.chdir('../zelbot/')
    #
    # @image.after_invoke
    # async def after_image(self, ctx):
    #     """
    #     Cd back to the main directory after uploading an image.
    #     """
    #     if ctx.args[2:]:  # Source was specified
    #         if os.path.basename(os.getcwd()) != 'lis-bot':
    #             os.chdir('../lis-bot/')

    @commands.group(aliases=['quotes'], invoke_without_command=True)
    async def quote(self, ctx, *, char: utils.QuoteChar=None, weighted=False):
        """
        Posts a quote from the specified character.
        ##nl## Use `cp quote` to get an overview of all available characters.
        ##nl## Use `cp quote random` to get a random quote.
        ##nl## Use `cp quote single/pair random/name` to ensure that
        only the specified type of quote is chosen.
        ##nl## Usually, each character has the same chance to get picked.
        If you want to take the quote amount into account, use
        `cp quote weighted random/name` instead.
        """
        if char is None:
            source_paginator = OverviewPaginator(self.bot, ctx, self)
            await source_paginator.prep_quote_char_paginator()
            await source_paginator.paginate()
            return

        available_chars = self.get_quote_chars(char, quotes)
        chosen_char = self.choose_quote_char(available_chars, quotes, weighted=weighted)
        if chosen_char is None:
            await ctx.send(f'`{char}` is not a valid character!')
            return

        quote = random.choice(quotes[chosen_char])
        if '&' in chosen_char:  # Highlight character names in dialogue pairs
            quote = self.apply_ini_markdown(quote)
        output = f'```{quote}```\n    `- {chosen_char}`'

        await ctx.send(output)

    @quote.command(name='weighted', hidden=True)
    async def quote_weighted(self, ctx, *, char: utils.QuoteChar=None):
        """
        Invoke the quote command, but change the normally unreachable
        `weighted` param to True, so the choice takes the amount
        of quotes that each character has into account.
        """
        if char is None:
            return
        await utils.invoke_with_checks(ctx, 'quote', char=char, weighted=True)

    @quote.command(name='single', hidden=True)
    async def quote_single(self, ctx, *, char: utils.QuoteChar=None):
        """
        Works the same as the quote command, except for ensuring
        that only quotes of single characters get used.
        """
        if char is None:
            return
        if char.split()[0] == 'Weighted':
            await ctx.send('The `quote single` command does'
                           ' not support the weighted option.')
            return

        matched_chars = self.get_quote_chars(char, quotes)
        if matched_chars is None:
            await ctx.send(f'`{char}` is not a valid character!')
            return

        available_chars = [char_ for char_ in matched_chars
                           if '&' not in char_]
        if not available_chars:
            await ctx.send(f'Could not match any single character for `{char}`.')
            return

        chosen_char = self.choose_quote_char(available_chars, quotes)
        quote = random.choice(quotes[chosen_char])
        output = f'```{quote}```\n    `- {chosen_char}`'

        await ctx.send(output)

    @quote.command(name='double', aliases=['pair'])
    async def quote_double(self, ctx, *, char: utils.QuoteChar=None):
        """
        Works the same as the quote command, except for ensuring
        that only quotes of pairs get used.
        """
        if char is None:
            return
        if char.split()[0] == 'Weighted':
            await ctx.send('The `quote pair` command does'
                           ' not support the weighted option.')
            return

        matched_chars = self.get_quote_chars(char, quotes)
        if matched_chars is None:
            await ctx.send(f'`{char}` is not a valid character!')
            return

        available_chars = [char_ for char_ in matched_chars
                           if '&' in char_]
        if not available_chars:
            await ctx.send(f'Could not match any pair for `{char}`.')
            return

        chosen_char = self.choose_quote_char(available_chars, quotes)
        quote = random.choice(quotes[chosen_char])
        quote = self.apply_ini_markdown(quote)
        output = f'```{quote}```\n    `- {chosen_char}`'

        await ctx.send(output)

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
                        value='[dog_gum](https://twitter.com/dog_gum)',
                        inline=True)
        embed.add_field(name='Invite Link',
                        value=f'[Click here]({config.invite_link})',
                        inline=True)
        embed.set_image(url=config.junkyard_url)
        embed.set_footer(text='https://github.com/Zelbot')

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(CMDS(bot))
