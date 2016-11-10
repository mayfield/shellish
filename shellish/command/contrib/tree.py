"""
Command tree.
"""

import collections
from .. import command
from ... import layout


class Tree(command.Command):
    """ Show a command tree. """

    name = 'tree'
    use_pager = True

    def setup_args(self, parser):
        pass

    def command_choices(self, prefix, args):
        return frozenset(x for x in self.parent.subcommands
                         if x.startswith(prefix))

    def run(self, args):
        root = self.parent
        tree = self.walkinto(root)
        layout.treeprint({root.name: tree})

    def walkinto(self, command):
        tree = collections.OrderedDict()
        if not command.subcommands:
            return command.title or command.name
        else:
            for key, cmd in command.subcommands.items():
                tree[key] = self.walkinto(cmd)
        return tree
