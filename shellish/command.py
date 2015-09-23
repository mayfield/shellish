"""
The merger of argparse and cmd goes here.  This holds the main base class
used by all commands.
"""

import argparse
import collections
import functools
import inspect
import io
import itertools
import os
import os.path
import shlex
import time
import traceback
from . import completer, shell, layout

__public__ = ['Command', 'autocommand', 'SystemCompletionSetup']


class Command(object):
    """ The primary encapsulation for a shellish command.  Each command or
    subcommand should be an instance of this class.  The docstring for sub-
    classes is used in --help output for this command and is required. """

    name = None
    ArgumentParser = argparse.ArgumentParser
    ArgumentFormatter = argparse.RawDescriptionHelpFormatter
    Shell = shell.Shell

    def setup_args(self, parser):
        """ Subclasses should provide any setup for their parsers here. """
        pass

    def prerun(self, args):
        """ Hook to do thing prior to any invocation. """
        pass

    def run(self, args):
        """ Primary entry point for command exec. """
        self.argparser.print_usage()
        raise SystemExit(1)

    def __init__(self, parent=None, doc=None, name=None, **context):
        self.doc = doc or inspect.getdoc(self)
        if name:
            self.name = name
        self.shell = None
        self.subcommands = []
        self.default_subcommand = None
        self.context_keys = set()
        self.inject_context(context)
        self.parent = parent
        self.subparsers = None
        self.argparser = self.create_argparser()
        self.last_invoke = None
        self.setup_args(self.argparser)

    def __call__(self, args=None, argv=None):
        """ If a subparser is present and configured  we forward invocation to
        the correct subcommand method. If all else fails we call run(). """
        if args is None:
            arg_input = shlex.split(argv) if argv is not None else None
            args = self.argparser.parse_args(arg_input)
        commands = self.get_commands_from(args)
        self.last_invoke = time.monotonic()
        if self.subparsers:
            try:
                command = commands[self.depth]
            except IndexError:
                if self.default_subcommand:
                    parser = self.default_subcommand.argparser
                    parser.parse_args([], namespace=args)
                    return self(args)  # retry
            else:
                self.prerun(args)
                return command(args)
        self.prerun(args)
        return self.run(args)

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, parent):
        """ Copy context from the parent into this instance as well as
        adjusting or depth value to indicate where we exist in a command
        tree. """
        self._parent = parent
        if parent:
            pctx = dict((x, getattr(parent, x)) for x in parent.context_keys)
            self.inject_context(pctx)
            self.depth = parent.depth + 1
            for command in self.subcommands:
                command.parent = self  # bump.
        else:
            self.depth = 0

    def inject_context(self, __context_dict__=None, **context):
        """ Map context dict to this instance as attributes and keep note of
        the keys being set so we can pass this along to any subcommands. """
        context = context or __context_dict__
        self.context_keys |= set(context.keys())
        for key, value in context.items():
            setattr(self, key, value)
        for command in self.subcommands:
            command.inject_context(context)

    @property
    def prog(self):
        return self.argparser.prog

    @prog.setter
    def prog(self, prog):
        """ Update ourself and any of our subcommands. """
        self.argparser.prog = prog
        fmt = '%s %%s' % prog if prog else '%s'
        for command in self.subcommands:
            command.prog = fmt % command.name

    @property
    def depth(self):
        return self._depth

    @depth.setter
    def depth(self, value):
        """ Update ourself and any of our subcommands. """
        for command in self.subcommands:
            command.depth = value + 1
            del command.argparser._defaults['command%d' % self._depth]
            command.argparser._defaults['command%d' % value] = command
        self._depth = value

    def interact(self):
        """ Run this command in shell mode.  Note that this loops until the
        user quits the session. """
        shell = self.Shell(self)
        self.inject_context(shell=shell)
        shell.cmdloop()

    def add_argument(self, *args, complete=None, **kwargs):
        """ Allow cleaner action supplementation. """
        action = self.argparser.add_argument(*args, **kwargs)
        if complete:
            action.complete = complete
        return action

    def create_argparser(self):
        """ Factory for arg parser.  Can be overridden as long as it returns
        an ArgParser compatible instance. """
        desc = self.clean_docstring()[1]
        return self.ArgumentParser(self.name, description=desc,
                                   formatter_class=self.ArgumentFormatter)

    def clean_docstring(self):
        """ Return sanitized docstring from this class.
        The first line of the docstring is the title, and remaining lines are
        the details, aka git style. """
        if not self.doc:
            raise SyntaxError('Docstring missing for: %s' % self)
        doc = [x.strip() for x in self.doc.splitlines()]
        if not doc[0]:
            doc.pop(0)  # Some people leave the first line blank.
        title = doc.pop(0)
        if doc:
            desc = '%s\n\n%s' % (title, '\n'.join(doc))
        else:
            desc = title
        return title, desc

    def complete_wrap(self, *args, **kwargs):
        """ Readline eats exceptions raised by completer functions. """
        try:
            return self._complete_wrap(*args, **kwargs)
        except BaseException as e:
            traceback.print_exc()
            raise e

    def _complete_wrap(self, text, line, begin, end):
        """ Get and format completer choices.  Note that all internal calls to
        completer functions must use [frozen]set()s but this wrapper has to
        return a list to satisfy cmd.Cmd. """
        choices = self.complete(text, line, begin, end)
        sz = len(choices)
        if sz == 1:
            return ['%s ' % shlex.quote(choices.pop())]
        elif sz > 2:
            # We don't need the sentinel choice to prevent completion
            # when there is already more than 1 choice.
            choices -= {completer.ActionCompleter.sentinel}
        # Python's readline module is hardcoded to not insert spaces so we
        # have to add a space to each response to get more bash-like behavior.
        return ['%s ' % x for x in choices]

    def columnize(self, *args, **kwargs):
        return layout.columnize(*args, **kwargs)

    def tabulate(self, *args, **kwargs):
        return layout.tabulate(*args, **kwargs)

    def vtmlprint(self, *args, **kwargs):
        return layout.vtmlprint(*args, **kwargs)

    def tree(self, *args, **kwargs):
        return layout.dicttree(*args, **kwargs)

    def complete(self, text, line, begin, end):
        """ Do naive argument parsing so the completer has better ability to
        understand expansion rules. """
        line = line[:end]  # Ignore characters following the cursor.
        args = self.split_line(line)[1:]
        options = self.deep_scan_parser(self.argparser)

        # Walk into options tree if subcommands are detected.
        last_subcommand = None
        while True:
            for key, completers in options.items():
                if key in args and hasattr(completers[0], 'items'):
                    args.remove(key)
                    last_subcommand = key
                    options = completers[0]
                    break
            else:
                break

        if text == last_subcommand:
            # We have to specially catch the case where the last argument is
            # the key used to find our subparser.  More specifically when the
            # cursor is not preceded by a space too, as this prevents the
            # completion routines from continuing.  The simplest way without
            # complicating the algo for coming up with our options list is to
            # simply shortcut the completer by returning a single item.
            # Subsequent tabs will work normally.
            return {text}

        # Look for incomplete actions.
        choices = set(options) - {None}
        arg_buf = []
        pos_args = []
        trailing_action = None
        # The slice below skips the last arg if it is 'active'.
        for x in reversed(args[:-1 if text else None]):
            if x in options:
                action = options[x][0]
                action.consume(arg_buf)
                pos_args.extend(arg_buf)
                del arg_buf[:]
                if not trailing_action:
                    trailing_action = action
                    if not action.full:
                        if action.reached_min:
                            choices |= action(self, text)
                            choices -= {action.key}
                        else:
                            choices = action(self, text)
                            break
            else:
                arg_buf.insert(0, x)
        pos_args.extend(arg_buf)

        # Feed any remaining arguments in the buffer to positionals so long as
        # there isn't a trailing action that can still consume.
        if None in options and (not trailing_action or trailing_action.full):
            for x_action in options[None]:
                x_action.consume(pos_args)
                if not x_action.reached_min:
                    choices = x_action(self, text)
                    break
                elif not x_action.full:
                    choices |= x_action(self, text)

        return set(x for x in choices if x.startswith(text))

    def split_line(self, line):
        """ Try to do pure shlex.split unless it can't parse the line. In that
        case we trim the input line until shlex can split the args and tack the
        unparsable portion on as the last argument. """
        remainder = []
        while True:
            try:
                args = shlex.split(line)
            except ValueError:
                remainder.append(line[-1])
                line = line[:-1]
            else:
                if remainder:
                    args.append(''.join(reversed(remainder)))
                return args

    @functools.lru_cache()
    def deep_scan_parser(self, parser):
        results = collections.defaultdict(list)
        for x in parser._actions:
            ac = completer.ActionCompleter(x)
            if ac.subparsers:
                for key, xx in ac.subparsers.items():
                    results[key].append(self.deep_scan_parser(xx))
            else:
                results[ac.key].append(ac)
        return results

    def get_commands_from(self, args):
        """ We have to code the key names for each depth.  This method scans
        for each level and returns a list of the command arguments. """
        commands = []
        for i in itertools.count(0):
            try:
                commands.append(getattr(args, 'command%d' % i))
            except AttributeError:
                break
        return commands

    def add_subcommand(self, command, default=False):
        if isinstance(command, type):
            command = command()
        command.parent = self
        if command.name is None:
            raise TypeError('Cannot add unnamed command: %s' % command)
        if not self.subparsers:
            desc = 'Provide a subcommand argument to perform an operation.'
            addsub = self.argparser.add_subparsers
            self.subparsers = addsub(title='subcommands', description=desc,
                                     metavar='COMMAND')
        if default:
            if self.default_subcommand:
                raise ValueError("Default subcommand already exists.")
            self.default_subcommand = command
        title, desc = command.clean_docstring()
        help_fmt = '%s (default)' if default else '%s'
        help = help_fmt % title
        command.prog = '%s %s' % (self.prog, command.name)
        command.argparser._defaults['command%d' % self.depth] = command
        action = self.subparsers._ChoicesPseudoAction(command.name, (), help)
        self.subparsers._choices_actions.append(action)
        self.subparsers._name_parser_map[command.name] = command.argparser
        self.subcommands.append(command)


class SystemCompletionSetup(Command):
    """ Generate a bash compatible completion script.

    Typically this command is run once and concatenated to your .<shell>rc
    file so completion targets for your shellish command can work from your
    system shell.  The idea is lifted directly from npm-completion. """

    name = 'completion'

    script_header = '''
        ###-begin-%(prog)s-%(name)s-###
        # %(prog)s command %(name)s script
        # Usage: %(prog)s %(name)s >> ~/.%(shell)src
    '''

    script_body = {
        'bash': '''
            _%(prog)s_%(name)s() {
                local words cword
                if type _get_comp_words_by_ref &>/dev/null; then
                    _get_comp_words_by_ref -n = -n @ -w words -i cword
                else
                    cword="$COMP_CWORD"
                    words=("${COMP_WORDS[@]}")
                fi
                local si="$IFS"
                IFS=$'\\n' COMPREPLY=($(COMP_CWORD="$cword" \\
                                     COMP_LINE="$COMP_LINE" \\
                                     COMP_POINT="$COMP_POINT" \\
                                     %(prog)s %(name)s --seed "${words[@]}" \\
                                     )) || return $?
                IFS="$si"
            }
            complete -o default -F _%(prog)s_%(name)s %(prog)s
        ''',
        'zsh': '''
            _%(prog)s_%(name)s() {
                local si=$IFS
                compadd -- $(COMP_CWORD=$((CURRENT-1)) \\
                             COMP_LINE=$BUFFER \\
                             COMP_POINT=0 \\
                             %(prog)s %(name)s --seed "${words[@]}" \\
                             2>/dev/null)
                IFS=$si
            }
            compdef _%(prog)s_%(name)s %(name)s
        '''
    }

    script_footer = '''###-end-%(prog)s-$(name)s-###'''

    def log(self, *args):
        with open("ecm-complete.log", 'a') as f:
            f.write(' '.join(map(repr, args)) + '\n')

    def setup_args(self, parser):
        self.add_argument('--seed', nargs=argparse.REMAINDER)

    def run(self, args):
        if not args.seed:
            return self.show_setup()
        prog = args.seed.pop(0)
        shift = len(prog) + 1
        index = int(os.getenv('COMP_CWORD')) - 1
        line = os.getenv('COMP_LINE')[shift:]
        beginold = int(os.getenv('COMP_POINT')) - shift
        begin = len(' '.join(args.seed[:index]))
        end = len(line)

        self.log('index', index)
        self.log('line', line)
        self.log('begin', begin)
        self.log('beginold', beginold)
        self.log('end', end)
        self.log('seed', args.seed)

        shell = self.Shell(self.parent)
        if begin > 0:
            cmd = shell.parseline(line)[0]
            self.log('CMMMM', cmd)
            if cmd == '':
                compfunc = shell.completedefault
            else:
                try:
                    compfunc = getattr(shell, 'complete_' + cmd)
                except AttributeError:
                    compfunc = shell.completedefault
        else:
            compfunc = shell.completenames
        self.log(compfunc)
        for x in compfunc(args.seed[index], line, begin, end):
            self.log("choice", x.rstrip())
            print(x.rstrip())

    def show_setup(self):
        """ Provide a helper script for the user to setup completion. """
        shell = os.getenv('SHELL')
        if not shell:
            raise SystemError("No $SHELL env var found")
        shell = os.path.basename(shell)
        if shell not in self.script_body:
            raise SystemError("Unsupported shell: %s" % shell)
        tplvars = {
            "prog": '-'.join(self.prog.split()[:-1]),
            "shell": shell,
            "name": self.name
        }
        print(self.trim(self.script_header % tplvars))
        print(self.trim(self.script_body[shell] % tplvars))
        print(self.trim(self.script_footer % tplvars))

    def trim(self, text):
        """ Trim whitespace indentation from text. """
        lines = text.splitlines()
        firstline = lines[0] or lines[1]
        indent = len(firstline) - len(firstline.lstrip())
        return '\n'.join(x[indent:] for x in lines if x.strip())


class AutoCommand(Command):
    """ Auto command ABC.  This command wraps a generic function and tries
    to map the function signature to a parser configuration.  Use the
    @autocommand decorator to use it. """

    def __init__(self, *args, func=None, **kwargs):
        self.func = func
        super().__init__(*args, **kwargs)

    def run(self, args):
        """ Convert the unordered args into function arguments. """
        args = vars(args)
        positionals = []
        keywords = {}
        for action in self.argparser._actions:
            if not hasattr(action, 'label'):
                continue
            if action.label == 'positional':
                positionals.append(args[action.dest])
            elif action.label == 'varargs':
                positionals.extend(args[action.dest])
            elif action.label == 'keyword':
                keywords[action.dest] = args[action.dest]
            elif action.label == 'varkwargs':
                kwpairs = iter(args[action.dest] or [])
                for key in kwpairs:
                    try:
                        key, value = key.split('=', 1)
                    except ValueError:
                        value = next(kwpairs)
                        key = key.strip('-')
                    keywords[key] = value
            else:
                raise RuntimeError("XXX: Impossible?")
        return self.func(*positionals, **keywords)

    def setup_args(self, default_parser):
        sig = inspect.signature(self.func)
        got_keywords = False
        for name, param in sig.parameters.items():
            label = ''
            options = {}
            help = None
            parser = default_parser
            if param.annotation is not sig.empty:
                options['type'] = param.annotation
            elif param.default not in (sig.empty, None):
                options['type'] = type(param.default)
            if param.kind in (param.POSITIONAL_OR_KEYWORD,
                              param.KEYWORD_ONLY):
                if param.kind == param.KEYWORD_ONLY or \
                   param.default is not sig.empty:
                    if isinstance(param.default, io.IOBase):
                        defvalue = param.default.name
                    else:
                        defvalue = str(param.default)
                    help = "(default: %s)" % defvalue
                    name = '--%s' % name
                    label = 'keyword'
                    got_keywords = True
                else:
                    label = 'positional'
            elif param.kind == param.VAR_POSITIONAL:
                if got_keywords:
                    # Logically impossible to handle this since keyword
                    # arguments are always expressed as key/value pairs and
                    # this language feature is based on giving a keyword
                    # argument by just its position.
                    raise ValueError("Unsupported function signature: %s" %
                                     sig)
                help = "variable positional args"
                options['nargs'] = '*'
                name = '*%s' % name
                label = 'varargs'
            elif param.kind == param.VAR_KEYWORD:
                options['nargs'] = argparse.REMAINDER
                name = '--%s' % name
                label = 'varkwargs'
                help = 'variable key/value args [[--key value] || ' \
                       '[key=value] ...]'
            if param.default not in (sig.empty, None):
                options['default'] = param.default
            if help:
                options['help'] = help
            if options.get('type'):
                try:
                    options['metavar'] = options['type'].__name__.upper()
                except:
                    pass
            action = parser.add_argument(name, **options)
            action.label = label


def autocommand(func):
    """ A simplified decorator for making a single function a Command
    instance.  In the future this will leverage PEP0484 to do really smart
    function parsing and conversion to argparse actions. """
    doc = inspect.getdoc(func) or 'Auto command for: %s' % func.__name__
    return AutoCommand(doc=doc, name=func.__name__, func=func)
