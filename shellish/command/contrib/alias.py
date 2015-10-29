"""
Show and edit alises.
"""

from .. import command


class Alias(command.Command):
    """ Show and edit command aliases. """

    name = 'alias'

    def setup_args(self, parser):
        self.add_argument('alias', nargs='?')
        super().setup_args(parser)

    def run(self, args):
        if args.alias:
            try:
                print(args.alias, '=', self.session.aliases[args.alias])
            except KeyError:
                raise SystemExit("Invalid alias: %s" % args.alias)
        else:
            for k, v in self.session.aliases.items():
                print(k, '=', v)
