"""
Show the INI config(s) used by a command tree.
"""

from .. import command


class Show(command.Command):
    """ Show current INI configuration.

    Programs may make use of a configuration file which is usually located in
    your $HOME directory as .<prog>_config.  The file is a standard INI
    style config file where each `[section]` is the full path of a command
    including spaces. """

    name = 'show'

    def setup_args(self, parser):
        self.add_argument('section', nargs='?', help='Only show config for '
                          'this section.')
        self.add_argument('--all', '-a', action='store_true', help='Show '
                          'all sections')
        super().setup_args(parser)

    def run(self, args):
        if args.section:
            try:
                config = {args.section: self.session.config[args.section]}
            except KeyError:
                raise SystemExit("Invalid section: %s" % args.section)
        else:
            config = self.session.config
        for section, values in config.items():
            if values or args.all:
                print("[%s]" % section)
                for k, v in values.items():
                    print("     %s = %s" % (k, v))
                print()


class INI(command.Command):
    """ INI style configuration.
    Commands support user configuration in an INI style config file. """

    name = 'ini'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_subcommand(Show, default=True)
