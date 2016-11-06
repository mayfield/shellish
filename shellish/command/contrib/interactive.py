"""
Command for interactive sessions only.
"""

from .. import command
from ... import rendering


class Help(command.Command):
    """ Show help for a command. """

    name = 'help'
    use_pager = True

    def setup_args(self, parser):
        self.add_argument('command', nargs='?', complete=self.command_choices,
                          help='Command name to show help for.')

    def command_choices(self, prefix, args):
        return frozenset(x for x in self.parent.subcommands
                         if x.startswith(prefix))

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
        print(formatter.format_help())
        print('  ALIAS')
        for k, v in self.session.aliases.items():
            print('    %-13s%s %s' % (k, rendering.beststr(' ⇨', '->'),
                  v.strip()))


class Exit(command.Command):
    """ Exit an interactive session. """

    name = 'exit'

    def run(self, args):
        self.session.exit()


class Reset(command.Command):
    """ Reset the TTY. """

    name = 'reset'

    def run(self, args):
        print('\033c')


class Pager(command.Command):
    """ Enable or disable the pager for commands. """

    name = 'pager'

    def enable(self, args):
        if self.session.allow_pager:
            raise SystemExit("Already enabled")
        self.session.allow_pager = True

    def disable(self, args):
        if not self.session.allow_pager:
            raise SystemExit("Already disabled")
        self.session.allow_pager = False

    def setup_args(self, parser):
        self.add_subcommand(command.Command(name='enable', run=self.enable))
        self.add_subcommand(command.Command(name='disable', run=self.disable))

    def run(self, args):
        if self.session.allow_pager:
            self.session.allow_pager = False
            print("Disabled pager")
        else:
            self.session.allow_pager = True
            print("Enabled pager: %s" % self.get_config('core').get('pager'))
