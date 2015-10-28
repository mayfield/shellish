"""
Show the configs used by a command tree.
"""

from . import command


class ShowConfig(command.Command):
    """ Show current command configuration.

    Commands may make use of a configuration file which is usually located in
    your $HOME directory as .<command>_config.  The file is a standard INI
    style config file where each `[section]` is the full path of a command
    including spaces.
    """

    name = 'show-config'

    def setup_args(self, parser):
        self.add_argument('command', nargs='?', help='Only show help for '
                          'this command.')
        super().setup_args(parser)

    def run(self, args):
        print(self.session.config)
