# BUILTIN
import inspect
# PIP
from discord.ext import commands


class Help(commands.Cog):

    __slots__ = ('bot', )

    def __init__(self, bot):
        self.bot = bot

    def get_docstring(self, cls, method):
        """
        Retrieve the docstring of a function.
        """
        cls = str(cls)
        method = str(method)
        for attribute_tuple in inspect.getmembers(self.bot.cogs[cls]):
            if attribute_tuple[0] == method:
                try:
                    return self.format_docstring(attribute_tuple[1].help)
                except AttributeError:
                    try:
                        return self.format_docstring(attribute_tuple[1].__doc__)
                    except AttributeError:
                        return 'No help text found'

    @staticmethod
    def format_docstring(string_):
        """
        Replace appearances of ##nl## with an actual newline character
        and strip the occasional whitespace.
        """
        joined = ' '.join(string_.split())
        replaced = joined.replace('##nl##', '\n')
        stripped = '\n'.join([line.strip() for line in replaced.split('\n')])
        return stripped

    def prep_doc_and_aliases(self, cog, command):
        """
        Prepare a more tidy output in the form of
        # -----
        `command - Alias: alias`
        docstring
        # -----
        if aliases are present.
        """
        docstring = self.get_docstring(cog, command.name)

        if command.aliases:
            names = f'{command.name} - Alias'
            if len(command.aliases) > 1:
                names += f'es: {", ".join(command.aliases)}'
            else:
                names += f': {command.aliases[0]}'
        else:
            names = command.name

        return f'`{names}`\n{docstring}'

    async def prep_cog_output(self, ctx, cog, title):
        """
        Prepare the whole output of a single cog.
        """
        output = f'```md\n<{ctx.me.name.split()[0]} {title}>```\n'

        for cmd in self.bot.cogs[cog].get_commands():
            if cmd.hidden is True:
                continue
            output += f'{self.prep_doc_and_aliases(cog, cmd)}\n\n'

        return output

    @commands.command()
    async def help(self, ctx):
        """
        Display help information about the commands in the CMDS cog.
        """
        await ctx.send(await self.prep_cog_output(ctx, 'CMDS', 'Command Help'))

    @commands.command()
    async def devhelp(self, ctx):
        """
        Display help information about the commands in the Owner cog.
        """
        await ctx.send(await self.prep_cog_output(ctx, 'Owner', 'Owner Command Help'))


def setup(bot):
    bot.add_cog(Help(bot))
