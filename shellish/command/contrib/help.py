"""
Alternate form of getting help.
"""

import difflib
import sys
from .. import command
from ... import rendering


class Help(command.Command):
    """ Show help for a command. """

    name = 'help'
    use_pager = True

    def setup_args(self, parser):
        self.add_argument('command', nargs='*', complete=self.command_choices,
                          help='Command name to show help of.')

    def command_choices(self, prefix, args):
        if args.command:
            cmd = self.find_command(args.command[:-1 if prefix else None])
        else:
            cmd = self.find_root()
        return frozenset(x for x in cmd.subcommands if x.startswith(prefix))

    def stderr(self, *args, **kwargs):
        return rendering.vtmlprint(*args, file=sys.stderr, **kwargs)

    def find_command(self, path):
        cmdptr = self.find_root()
        for i, cmd in enumerate(path):
            try:
                cmdptr = cmdptr.subcommands[cmd]
            except KeyError:
                raise LookupError(cmdptr, i)
        return cmdptr

    def run(self, args):
        if not args.command:
            self.find_root().argparser.print_help()
            return
        try:
            cmd = self.find_command(args.command)
        except LookupError as e:
            good_cmd, fail_idx = e.args
            good = ' '.join(args.command[:fail_idx]) + ' ' if fail_idx else ''
            bad = ' '.join(args.command[fail_idx:])
            self.stderr('<red>Command not found:</red> %s<b><red>%s' % (good,
                        bad))
            for x in difflib.get_close_matches(args.command[fail_idx],
                                               good_cmd.subcommands):
                self.stderr('    Did you mean: %s<b>%s</b>?' % (good, x))
            raise SystemExit(1)
        else:
            cmd.argparser.print_help()
