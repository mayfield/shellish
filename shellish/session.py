"""
Session context for commands.  This provides singular state mgmt for a tree
of commands as well as the implementation for interactive mode.
"""

import ast
import configparser
import os.path
import pdb
import readline
import shellish
import sys
import traceback
from . import eventing, layout


class SessionQuit(Exception):
    pass


class Session(eventing.Eventer):
    """ The session manager for a tree of commands. """

    var_dir = os.path.expanduser('~')
    exception_verbosity = 'traceback'

    def __init__(self, root_command, name=None):
        self.root_command = root_command
        self.name = name or root_command.name
        self.config = self.load_config()
        super().__init__()

    def map_subcommands(self, func):
        """ Run `func` against all the subcommands attached to our root
        command. """

        def crawl(cmd):
            for sc in cmd.subcommands.values():
                yield from crawl(sc)
            yield cmd
        return map(func, crawl(self.root_command))

    def load_config(self):
        filename = os.path.join(self.var_dir, '.%s_config' % self.name)
        config = configparser.ConfigParser()
        config.read_dict(self.default_config())
        config.read_dict(self.command_default_configs())
        config.read(filename)
        return config

    def default_config(self):
        return {}

    def command_default_configs(self):
        getconfig = lambda cmd: (cmd.prog, cmd.default_config())
        return dict(self.map_subcommands(getconfig))


class InteractiveSession(Session):
    """ Interactive session mgmt. """

    default_prompt_format = '[{name}] $'
    intro = 'Type "help" or "?" to list commands and "exit" to quit.'
    completer_delim_includes = frozenset()
    completer_delim_excludes = frozenset('-+@:/~*')
    pad_completion = True

    def __init__(self, root_command, **kwargs):
        root_command.prog = ''
        super().__init__(root_command, **kwargs)
        self.setup_readline()
        raw_prompt = self.config['ui']['prompt_format']
        self.prompt_format = ast.literal_eval("'%s '" % raw_prompt)

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
        filename = os.path.join(self.var_dir, '.%s_history' % self.name)
        try:
            readline.read_history_file(filename)
        except FileNotFoundError:
            pass
        return filename

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

    def cmd_split(self, line):
        """ Get the command assosiated with this input line. """
        cmd, *args = line.lstrip().split(' ', 1)
        return self.root_command.subcommands[cmd], ' '.join(args)

    def completer_hook(self, text, state):
        if state == 0:
            linebuf = readline.get_line_buffer()
            line = linebuf.lstrip()
            stripped = len(linebuf) - len(line)
            begin = readline.get_begidx() - stripped
            end = readline.get_endidx() - stripped
            if begin > 0:
                try:
                    cmd, args = self.cmd_split(line)
                except KeyError:
                    return None
                cfunc = cmd.complete
            else:
                cfunc = self.complete_names
            if self.pad_completion:
                pad = lambda x: x + ' ' if not x.endswith(' ') or \
                                           x.endswith(r'\ ') else x
            else:
                pad = lambda x: x
            choices = self.complete_wrap(cfunc, text, line, begin, end)
            self.completer_cache = list(map(pad, choices))
        try:
            return self.completer_cache[state]
        except IndexError:
            return None

    def complete_wrap(self, func, *args, **kwargs):
        """ Readline eats exceptions raised by completer functions. """
        try:
            return func(*args, **kwargs)
        except BaseException as e:
            traceback.print_exc()
            raise e

    def complete_names(self, text, line, begin, end):
        return [x for x in self.root_command.subcommands
                if x.startswith(line)]

    def handle_cmd_exc(self, exc):
        """ Do any formatting of run_loop exceptions or simply reraise if the
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
            raise ValueError('Unexpected exception_verbosity: %s' %
                             self.exception_verbosity)

    def pretty_print_exc(self, exc):
        layout.vtmlprint('<red>Command Error: %s</red>' % exc)

    def run_loop(self):
        history_file = self.load_history()
        completer_save = readline.get_completer()
        readline.set_completer(self.completer_hook)
        readline.parse_and_bind('tab: complete')
        layout.vtmlprint(self.intro)
        try:
            self._runloop()
        finally:
            readline.set_completer(completer_save)
            readline.write_history_file(history_file)

    def _runloop(self):
        while True:
            try:
                line = input(self.prompt)
            except EOFError:
                print('^D')
                break
            except KeyboardInterrupt:
                print()
                continue
            if not line.strip():
                continue
            try:
                cmd, args = self.cmd_split(line)
            except KeyError as e:
                shellish.vtmlprint('<red>Invalid command: %s</red>' % e,
                                   file=sys.stderr)
                continue
            try:
                cmd(argv=args)
            except SessionQuit:
                break
            except KeyboardInterrupt:
                print()
            except SystemExit as e:
                if not str(e).isnumeric():
                    shellish.vtmlprint('<red>%s</red>' % e, file=sys.stderr)
            except Exception as e:
                self.handle_cmd_exc(e)

    def exit(self):
        raise SessionQuit()
