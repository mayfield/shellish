"""
Legacy `commands` proxy.
"""

from . import commands


class Tree(commands.Commands):
    """ [DEPRECATED - use commands instead] Show a command tree. """

    name = 'tree'
