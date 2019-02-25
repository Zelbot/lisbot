# BUILTIN
import os
import random
import string
# PIP
import discord
from discord.ext import commands
# CUSTOM
import config
from utils import utils
from data.quotes import quotes


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

    def choose_freecam_folder(self, args, return_urls=False):
        """
        Chooses a folder to use in the lis command.
        """
        freecam_path = os.path.join(os.getcwd(), 'images', 'Life_is_Strange')
        all_folders = [os.path.relpath(os.path.join(freecam_path, folder))
                       for folder in os.listdir(freecam_path)]

        urls = {}
        for folder in all_folders:
            url = self.generate_folder_url(os.path.basename(folder))
            urls[url] = folder
        if return_urls is True:
            return urls

        if args:
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
            # Choose any random folder if the search had no matches
            else:
                chosen_folder = random.choice(all_folders)

        # Choose any random folder if no source was provided
        else:
            chosen_folder = random.choice(all_folders)

        return chosen_folder

    def get_freecam_sources(self, args):
        """
        Prepares an overview of available sources for the lis command.
        """
        urls = self.choose_freecam_folder(args, return_urls=True)
        sorted_urls = sorted(list(urls.keys()))

        output = '**Available sources:**\n'
        for url in sorted_urls:
            output += f'  <{url}>\n'

        return output

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
            try:
                longest_str = len(max(name_list, key=len))
            except ValueError:  # Empty name list for custom quotes
                continue

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
        try:
            longest_quote = len(max(quotes_lens, key=len))
        except ValueError:  # Empty list for custom quotes
            return ''

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
    def choose_quote_char(char, quotes_dict):
        """
        Chooses a character name to be used in the quotes command.
        """
        if char.count('&') > 1:  # Only two people per pair allowed, ever
            return None

        # # Smol easter egg :)
        # if char.lower() == 'daddy':
        #     if random.randint(0, 1) == 0:
        #         return 'Mark Jefferson'
        #     if not any('daddy' in k.lower() for k in quotes_dict.keys()):
        #         char = 'Mark Jefferson &'  # Don't return as we want a random pair
        #     elif random.randint(0, 1) == 0:  # 'Daddy' in keys, do not guarantee a swap
        #         char = 'Mark Jefferson &'

        if char.lower() == 'random':
            return random.choice(list(quotes_dict.keys()))

        if char in quotes_dict:
            available_chars = [name for name in quotes_dict
                               if char in name]
            return random.choice(available_chars)
            # return char

        # char not in quotes_dict
        # Incomplete name, e.g. 'Max' instead of 'Max Caulfield'
        # Side effect: 'D' also chooses a character, i.e. 'Daniel Da Costa'
        if '&' in char:
            # Complete dialogue pairs like 'William Price & Chloe Price'
            if not char.endswith('&'):
                name1 = char.split('&')[0].strip()
                name2 = char.split('&')[1].strip()

                available_chars = [name for name in quotes_dict
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
                available_chars = [name for name in quotes_dict
                                   if '&' in name and char_name in name]

        # Any matches based on both first and last name
        else:
            available_chars = [name for name in quotes_dict
                               # if any(split.startswith(char) for split in name.split())]
                               if any(split.startswith(tuple(char.split()))
                                      for split in name.split())]

        # Also covers incorrect inputs, e.g. 'Max & Chloe &'
        if not available_chars:  # No matching name found
            return None
        return random.choice(available_chars)

    @commands.command()
    async def image(self, ctx, *args):
        """
        Posts an image about Life is Strange, supports matching based on sources.
        ##nl## Use `cp image overview` to get an overview of all available sources.
        """
        # Post an overview of available sources and return
        if args and args[0].lower() == 'overview':
            await ctx.send(self.get_freecam_sources(args))
            return

        chosen_folder = self.choose_freecam_folder(args)
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

    @commands.command()
    async def quote(self, ctx, *, char=None):
        """
        Chooses a quote from the specified character or a random one if `cp quote random` is used.
        """
        # Make a copy of the global imported quotes dict
        # and add extra quotes to the local (temporary) copy
        # (extras variable is imported from quotes_extras.py)

        if char is None:
            overview = self.get_quote_char_overview(quotes, 'Available Characters')
            await ctx.send(overview)
            return

        char = char.lower().title()
        char = char.replace('And', '&')

        chosen_char = self.choose_quote_char(char, quotes)
        if chosen_char is None:
            await ctx.send(f'`{char}` is not a valid character!')
            return

        quote = random.choice(quotes[chosen_char])
        if '&' in chosen_char:  # Highlight character names in dialogue pairs
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
        embed.add_field(name='Prog. Language',
                        value='Python',
                        inline=True)
        embed.add_field(name='Need Help?',
                        value='Use cphelp',
                        inline=True)
        embed.add_field(name='Avatar Author',
                        value='[dog_gum](https://twitter.com/dog_gum)',
                        inline=True)
        embed.set_image(url=config.junkyard_url)
        embed.set_footer(text='https://github.com/Zelbot')

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(CMDS(bot))
