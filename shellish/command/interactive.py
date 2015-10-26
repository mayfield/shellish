"""
Command for interactive sessions only.
"""

from . import base


class Help(base.Command):
    """ Show help for a command. """

    name = 'help'

    def setup_args(self, parser):
        self.add_argument('command', nargs='?', complete=self.command_choices,
                          help='Command name to show help for.')


    def command_choices(self, prefix, args):
        return frozenset(x for x in self.parent.subcommands
                         if x.startswith(prefix))

    def find_root(self):
        cmd = self
        while cmd.parent:
            cmd = cmd.parent
        return cmd

    def run(self, args):
        if not args.command:
            self.print_overview()
        else:
            try:
                command = self.parent.subcommands[args.command]
            except KeyError:
                raise SystemExit("Invalid command")
            command.argparser.print_help()

    def print_overview(self):
        ap = self.find_root().argparser
        formatter = ap._get_formatter()

        formatter.add_text(ap.description)
        for x in ap._action_groups:
            if x.title == 'subcommands':
                formatter.start_section(x.title)
                formatter.add_text(x.description)
                formatter.add_arguments(x._group_actions)
                formatter.end_section()
                break
        formatter.add_text(ap.epilog)
        ap._print_message(formatter.format_help())


class Exit(base.Command):
    """ Exit an interactive session. """

    name = 'exit'

    def run(self, args):
        self.session.exit()
