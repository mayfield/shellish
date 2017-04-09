"""
Command for interactive sessions only.
"""

from .. import command


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
