# BUILTIN
import random
# PIP
from discord.ext import commands
from numpy.random import choice
# CUSTOM
from utils import utils
from data.quotes import quotes

class Quotes(commands.Cog):

    __slots__ = ('bot', )

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """
        Check to see if the bot has the required permissions
        for these commands.
        """
        if ctx.channel.permissions_for(ctx.me).add_reactions is False:
            await ctx.send('I need `Add Reactions` permissions to work properly!')
            return False

        return True

    @staticmethod
    def apply_ini_markdown(quote):
        """
        Encloses character names from dialogue pairs in square brackets
        and adds ini markdown to highlight them.
        """
        lines = quote.split('\n')
        for index, line in enumerate(lines[:]):
            character = line.split(':')[0]
            sentence = ' '.join(line.split(':')[1:])
            lines[index] = f'[{character}]:{sentence}'

        quote_with_ini = 'ini\n' + '\n'.join(lines)
        return quote_with_ini


    def get_quote_char_overview(self, title):
        """
        Constructs an overview of the available characters
        for the quotes command, using markdown for highlighting.
        """
        overview = f'```css\n[{title}]```\n'
        overview += '```ml\n'
        overview += self.get_single_char_overview() + '\n\n'
        overview += self.get_char_pair_overview() + '\n```'
        return overview

    @staticmethod
    def get_single_char_overview(quotes):
        """
        Prepares an overview of all single characters.
        """
        single_chars = sorted([char for char in quotes if '&' not in char])
        quotes_lens = [str(len(quotes[char])) for char in single_chars]
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
                padded_count = str(len(quotes[name])).rjust(longest_quote)
                name_list[index] = padded_name + padded_count

            # Add padding and "quote" or "quotes"
            longest_str = len(max(name_list, key=len))
            for index, name in enumerate(name_list[:]):
                char_name = name.split('-')[0].strip()
                padded_str = name.ljust(longest_str + 1)

                if len(quotes[char_name]) == 1:
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
    def get_char_pair_overview(quotes):
        """
        Prepares an overview of all dialogue pairs.
        """
        char_pairs = sorted([char for char in quotes if '&' in char])
        quotes_lens = [str(len(quotes[char])) for char in char_pairs]
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
            padded_count = str(len(quotes[pair])).rjust(longest_quote)
            seconds_of_pairs[index] = padded_name + padded_count

        # Add padding and "quote" or "quotes"
        longest_str = len(max(seconds_of_pairs, key=len))
        for index, name in enumerate(seconds_of_pairs[:]):
            pair = char_pairs[index]
            padded_str = name.ljust(longest_str + 1)

            if len(quotes[pair]) == 1:
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
    def get_quote_chars(char):
        """
        Prepare a list of all matched characters for the quote commands.
        """
        if char.count('&') > 1:  # Only two people per pair allowed, ever
            return None

        if char.lower() == 'random':
            available_chars = list(quotes.keys())

        elif char in quotes:
            available_chars = [name for name in quotes.keys()
                               if char in name]

        # char not in quotes
        # Incomplete name, e.g. 'Max' instead of 'Max Caulfield'
        # Side effect: 'D' also chooses a character, i.e. 'Daniel Da Costa'
        elif '&' in char:
            # Complete dialogue pairs like 'William Price & Chloe Price'
            if not char.endswith('&'):
                name1 = char.split('&')[0].strip()
                name2 = char.split('&')[1].strip()

                available_chars = [name for name in quotes.keys()
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
                available_chars = [name for name in quotes.keys()
                                   if '&' in name and char_name in name]

        # Any matches based on both first and last name
        else:
            available_chars = [name for name in quotes.keys()
                               # if any(split.startswith(char) for split in name.split())]
                               if any(split_.startswith(tuple(char.split()))
                                      for split_ in name.split())]

        # Can be an empty list of no match was found
        return available_chars

    @staticmethod
    def choose_quote_char(characters, weighted=False):
        """
        Chooses a character name to be used in the quotes command.
        If weighted is True, the amount of quotes for each character
        is taken into account when the choice is made.
        """
        if not characters:
            return None
        if len(characters) == 1:
            return characters[0]

        if weighted is False:
            return random.choice(characters)

        chars = {name: list_ for name, list_ in quotes.items()
                 if name in characters}
        # Calculate a list of percentage-wise probabilities by dividing
        # the length of a single list through the sum of all lengths of all lists
        probabilities = [len(list_) / sum([len(l) for l in chars.values()])
                         for list_ in chars.values()]
        return choice(a=list(chars.keys()), p=probabilities)

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
            source_paginator = utils.OverviewPaginator(self.bot, ctx, self)
            await source_paginator.prep_quote_char_paginator()
            await source_paginator.paginate()
            return

        available_chars = self.get_quote_chars(char)
        chosen_char = self.choose_quote_char(available_chars, weighted=weighted)
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

    @quote.command(name='single', aliases=['solo'], hidden=True)
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

        matched_chars = self.get_quote_chars(char)
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

    @quote.command(name='double', aliases=['duo', 'pair'])
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

        matched_chars = self.get_quote_chars(char)
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


def setup(bot):
    bot.add_cog(Quotes(bot))
