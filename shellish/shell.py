"""
The interactive portions of shellish.
"""

import ast
import cmd
import configparser
import os.path
import pdb
import readline
import shlex
import sys
import traceback
from . import layout

__public__ = ['Shell']


class ShellQuit(Exception):
    pass


class Shell(cmd.Cmd):
    """ The interactive manager for a session of command calls.  This babysits
    a tree of commands until the user requests our exit. """

    default_prompt_format = '[{name}] $ '
    history_dir = os.path.expanduser('~')
    config_dir = os.path.expanduser('~')
    intro = 'Type "help" or "?" to list commands and "exit" to quit.'
    completer_delim_includes = frozenset()
    completer_delim_excludes = frozenset('-+@:')
    exception_verbosity = 'traceback'
    pad_completion = True

    def __init__(self, root_command):
        self.root_command = root_command
        self.name = root_command.name
        root_command.prog = ''
        self.config = self.load_config()
        self.setup_readline()
        raw_prompt = self.config['ui']['prompt_format']
        self.prompt_format = ast.literal_eval("'%s '" % raw_prompt)
        for x in root_command.subcommands:
            setattr(self, 'do_%s' % x.name, self.wrap_command_invoke(x))
            setattr(self, 'help_%s' % x.name, x.argparser.print_help)
            setattr(self, 'complete_%s' % x.name, x.complete_wrap)
        super().__init__()

    @property
    def prompt(self):
        return self.prompt_format.format(**self.prompt_info())

    def prompt_info(self):
        """ Return a dictionary of items that can be substituted into the
        prompt_format by the subclass or it's user if customized in the
        config file by them. """
        return {
            "name": self.name,
        }

    def default_config(self):
        return {
            "ui": {
                "prompt_format": self.default_prompt_format
            }
        }

    def setup_readline(self):
        delims = set(readline.get_completer_delims())
        delims |= self.completer_delim_includes
        delims -= self.completer_delim_excludes
        self.completer_delims = ''.join(delims)
        readline.set_completer_delims(self.completer_delims)

    def load_history(self):
        filename = os.path.join(self.history_dir, '.%s_history' % self.name)
        try:
            readline.read_history_file(filename)
        except FileNotFoundError:
            pass
        return filename

    def load_config(self):
        filename = os.path.join(self.config_dir, '.%s_config' % self.name)
        config = configparser.ConfigParser()
        config.read_dict(self.default_config())
        config.read(filename)
        return config

    def wrap_command_invoke(self, cmd):
        def wrap(arg):
            args = cmd.argparser.parse_args(shlex.split(arg))
            cmd(args)
        wrap.__doc__ = cmd.__doc__
        wrap.__name__ = 'do_%s' % cmd.name
        return wrap

    def get_names(self):
        names = super().get_names()
        commands = self.root_command.subcommands
        for op in ('help', 'do', 'complete'):
            names.extend('%s_%s' % (op, x.name) for x in commands)
        return names

    def complete(self, text, state):
        """Return the next possible completion for 'text'.

        If a command has not been entered, then complete against command list.
        Otherwise try to call complete_<command> to get list of completions.
        """
        if state == 0:
            super().complete(text, state)
            if self.pad_completion:
                pad = lambda x: x + ' ' if not x.endswith(' ') or \
                                           x.endswith(r'\ ') else x
                m = self.completion_matches
                m[:] = [pad(x) for x in m]
        try:
            return self.completion_matches[state]
        except IndexError:
            return None

    def emptyline(self):
        """ Do not re-run the last command. """
        pass

    def columnize(self, *args, **kwargs):
        return layout.columnize(*args, **kwargs)

    def tabulate(self, *args, **kwargs):
        return layout.tabulate(*args, **kwargs)

    def vtmlprint(self, *args, **kwargs):
        return layout.vtmlprint(*args, **kwargs)

    def tree(self, *args, **kwargs):
        return layout.dicttree(*args, **kwargs)

    def handle_cmd_exc(self, exc):
        """ Do any formatting of cmdloop exceptions or simply reraise if the
        error is bad enough. """
        if self.exception_verbosity == 'traceback':
            self.pretty_print_exc(exc)
            print(*traceback.format_exception(*sys.exc_info()))
            return
        elif self.exception_verbosity == 'debugger':
            pdb.set_trace()
            return
        elif self.exception_verbosity == 'raise':
            raise exc from None
        elif self.exception_verbosity == 'pretty':
            self.pretty_print_exc(exc)
            return
        else:
            raise ValueError("Unexpected exception_verbosity: %s" %
                             self.exception_verbosity)

    def pretty_print_exc(self, exc):
        self.vtmlprint("<b>Command Error:</b>", exc)

    def cmdloop(self):
        history_file = self.load_history()
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
            except Exception as e:
                self.handle_cmd_exc(e)
            finally:
                readline.write_history_file(history_file)
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
