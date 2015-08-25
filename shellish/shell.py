"""
The interactive portions of shellish.
"""

import cmd
import os.path
import readline
import shlex
import shutil
import sys

__public__ = ['Shell']


class ShellQuit(Exception):
    pass


class Shell(cmd.Cmd):
    """ The interactive manager for a session of command calls.  This babysits
    a tree of commands until the user requests our exit. """

    prompt = '$ '
    history_dir = os.path.expanduser('~')
    intro = 'Type "help" or "?" to list commands and "exit" to quit.'

    def __init__(self, root_command):
        self.root_command = root_command
        self.name = root_command.name
        self.history_file = os.path.join(self.history_dir,
                                         '.%s_history' % self.name)
        try:
            readline.read_history_file(self.history_file)
        except FileNotFoundError:
            pass
        for x in root_command.subcommands:
            setattr(self, 'do_%s' % x.name, self.wrap_command_invoke(x))
            setattr(self, 'help_%s' % x.name, x.argparser.print_help)
            setattr(self, 'complete_%s' % x.name, x.complete_wrap)
        delims = set(readline.get_completer_delims())
        readline.set_completer_delims(''.join(delims - set('-+@:')))
        super().__init__()

    def wrap_command_invoke(self, cmd):
        def wrap(arg):
            args = cmd.argparser.parse_args(shlex.split(arg))
            cmd.invoke(args)
        wrap.__doc__ = cmd.__doc__
        wrap.__name__ = 'do_%s' % cmd.name
        return wrap

    def get_names(self):
        names = super().get_names()
        commands = self.root_command.subcommands
        for op in ('help', 'do', 'complete'):
            names.extend('%s_%s' % (op, x.name) for x in commands)
        return names

    def complete_help(self, *args, **kwargs):
        topics = super().complete_help(*args, **kwargs)
        return ['%s ' % x.rstrip() for x in topics]

    def completenames(self, *args, **kwargs):
        names = super().completenames(*args, **kwargs)
        return ['%s ' % x.rstrip() for x in names]

    def emptyline(self):
        """ Do not re-run the last command. """
        pass

    def columnize(self, items, displaywidth=None):
        if displaywidth is None:
            displaywidth, h = shutil.get_terminal_size()
        return super().columnize(items, displaywidth=displaywidth)

    def cmdloop(self):
        intro = ()
        while True:
            try:
                super().cmdloop(*intro)
            except ShellQuit:
                return
            except KeyboardInterrupt:
                print()
            except SystemExit as e:
                if not str(e).isnumeric():
                    print(e, file=sys.stderr)
            finally:
                readline.write_history_file(self.history_file)
            if not intro:
                intro = ('',)

    def do_exit(self, arg):
        raise ShellQuit()

    def default(self, line):
        if line == 'EOF':
            print('^D')
            raise ShellQuit()
        else:
            return super().default(line)
