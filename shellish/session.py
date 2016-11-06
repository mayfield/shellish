"""
Session context for commands.  This provides singular state mgmt for a tree
of commands as well as the implementation for interactive mode.
"""

import ast
import configparser
import contextlib
import os.path
import pdb
import readline
import shutil
import sys
import traceback
from . import eventing, rendering


def _vprinterr(*args, **kwargs):
    return rendering.vtmlprint(*args, file=sys.stderr, **kwargs)


class SessionExit(BaseException):
    pass


class Session(eventing.Eventer):
    """ The session manager for a tree of commands. """

    var_dir = os.path.expanduser('~')
    command_error_verbosity = 'traceback'
    default_prompt_format = '[{name}] $'
    intro = 'Type "help" or "?" to list commands and "exit" to quit.'
    completer_delim_includes = frozenset()
    completer_delim_excludes = frozenset('-+@:/~*')
    pad_completion = True
    allow_pager = bool(os.environ.get('PAGER', True))

    @property
    def config_file(self):
        return '.%s_config' % self.name

    @property
    def history_file(self):
        return '.%s_history' % self.name

    def __init__(self, root_command, name=None):
        self.root_command = root_command
        self.name = name or root_command.name
        self.config = self.load_config()
        if 'alias' in self.config:
            self.aliases = self.config['alias']
        else:
            self.aliases = {}
        self.add_events(['precmd', 'postcmd'])
        raw_prompt = self.config['ui']['prompt_format']
        self.prompt_format = ast.literal_eval("'%s '" % raw_prompt)
        super().__init__()

    def default_config(self):
        return {
            "ui": {
                "prompt_format": self.default_prompt_format
            },
            "core": {
                "pager": "less -X -R -F -P's{desc}, line %l "
                         "(press h for help or q to quit)'"
            }
        }

    def load_config(self):
        filename = os.path.join(self.var_dir, self.config_file)
        config = configparser.ConfigParser(interpolation=None)
        config.read_dict(self.default_config())
        config.read_dict(self.command_default_configs())
        config.read(filename)
        return config

    def load_history(self):
        filename = os.path.join(self.var_dir, self.history_file)
        try:
            readline.read_history_file(filename)
        except FileNotFoundError:
            pass
        return filename

    def exit(self):
        """ Can be called by commands to stop an interactive session. """
        raise SessionExit()

    def map_subcommands(self, func):
        """ Run `func` against all the subcommands attached to our root
        command. """

        def crawl(cmd):
            for sc in cmd.subcommands.values():
                yield from crawl(sc)
            yield cmd
        return map(func, crawl(self.root_command))

    def command_default_configs(self):
        getconfig = lambda cmd: (cmd.config_section(), cmd.default_config())
        return dict(self.map_subcommands(getconfig))

    def execute(self, command, args):
        """ Event firing and exception conversion around command execution.
        Common exceptions are run through our exception handler for
        pretty-printing or debugging and then converted to SystemExit so the
        interpretor will exit without further ado (or be caught if
        interactive). """
        self.fire_event('precmd', command, args)
        try:
            try:
                result = command.run_wrap(args)
            except BaseException as e:
                self.fire_event('postcmd', command, args, exc=e)
                raise e
            else:
                self.fire_event('postcmd', command, args, result=result)
                return result
        except BrokenPipeError as e:
            _vprinterr('<dim><red>...broken pipe...</red></dim>')
            raise SystemExit(1) from e
        except KeyboardInterrupt as e:
            _vprinterr('<dim><red>...interrupted...</red></dim>')
            raise SystemExit(1) from e
        except SystemExit as e:
            if e.args and not isinstance(e.args[0], int):
                _vprinterr("<red>%s</red>" % e)
                raise SystemExit(1) from e
            raise e
        except Exception as e:
            self.handle_command_error(command, args, e)
            raise SystemExit(1) from e

    def handle_command_error(self, command, args, exc):
        """ Depending on how the session is configured this will print
        information about an unhandled command exception or possibly jump
        to some other behavior like a debugger. """
        verbosity = self.command_error_verbosity
        if verbosity == 'traceback':
            self.pretty_print_exc(command, exc, show_traceback=True)
        elif verbosity == 'debug':
            pdb.set_trace()
        elif verbosity == 'raise':
            raise exc
        elif verbosity == 'pretty':
            self.pretty_print_exc(command, exc)
        else:
            raise ValueError('Unexpected exception_verbosity: %s' %
                             verbosity)

    def pretty_print_exc(self, command, exc, show_traceback=False):
        cmdname = command.prog or command.name
        if not show_traceback:
            _vprinterr("<red>Command '%s' error: %s - %s</red>" % (cmdname,
                       type(exc).__name__, exc))
        else:
            _vprinterr("<red>Command '%s' error, traceback...</red>" %
                       cmdname)
            rendering.print_exception(exc, file=sys.stderr)

    @property
    def prompt(self):
        raw = self.prompt_format.format(**self.prompt_info())
        return rendering.vtmlrender(raw)

    def prompt_info(self):
        """ Return a dictionary of items that can be substituted into the
        prompt_format by the subclass or its user if customized in the
        config file. """
        return {
            "name": self.name,
        }

    def cmd_split(self, line):
        """ Get the command associated with this input line. """
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
        # Workaround readline's one-time-read of terminal width.
        termcols = shutil.get_terminal_size()[0]
        readline.parse_and_bind('set completion-display-width %d' % termcols)
        try:
            return func(*args, **kwargs)
        except:
            traceback.print_exc()
            raise

    def complete_names(self, text, line, begin, end):
        choices = set(self.root_command.subcommands)
        choices |= set(self.aliases)
        return [x for x in choices if x.startswith(line)]

    @contextlib.contextmanager
    def setup_readline(self):
        """ Configure our tab completion settings for a context and then
        restore them to previous settings on exit. """
        readline.parse_and_bind('tab: complete')
        completer_save = readline.get_completer()
        delims_save = readline.get_completer_delims()
        delims = set(delims_save)
        delims |= self.completer_delim_includes
        delims -= self.completer_delim_excludes
        readline.set_completer(self.completer_hook)
        try:
            readline.set_completer_delims(''.join(delims))
            try:
                yield
            finally:
                readline.set_completer_delims(delims_save)
        finally:
            readline.set_completer(completer_save)

    def run_loop(self):
        """ Main entry point for running in interactive mode. """
        self.root_command.prog = ''
        history_file = self.load_history()
        rendering.vtmlprint(self.intro)
        try:
            self.loop()
        finally:
            readline.write_history_file(history_file)

    def loop(self):
        """ Inner loop for interactive mode.  Do not call directly. """
        while True:
            with self.setup_readline():
                try:
                    line = input(self.prompt)
                except EOFError:
                    _vprinterr('^D')
                    break
                except KeyboardInterrupt:
                    _vprinterr('^C')
                    continue
            if not line.strip():
                continue
            try:
                cmd, args = self.cmd_split(line)
            except KeyError as e:
                _vprinterr('<red>Invalid command: %s</red>' % e)
                continue
            try:
                cmd(argv=args)
            except SessionExit:
                break
            except SystemExit as e:
                pass
