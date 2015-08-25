"""
The merger of argparse and cmd goes here.  This holds the main base class
used by all commands.
"""

import argparse
import collections
import functools
import itertools
import shlex
import time
import traceback
from . import debug, completer

__public__ = ['Command']


class Command(object):
    """ The primary encapsulation for a shellish command.  Each command or
    subcommand should be an instance of this class.  The docstring for sub-
    classes is used in --help output for this command and is required. """

    name = None  # Single word string required by subclass.

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

    def add_argument(self, *args, complete=None, **kwargs):
        """ Allow cleaner action supplementation. """
        action = self.argparser.add_argument(*args, **kwargs)
        if complete:
            action.complete = complete
        return action

    def __init__(self, parent=None, **context):
        self.inject_context(parent, context)
        self.parent = parent
        self.depth = (parent.depth + 1) if parent else 0
        self.subcommands = []
        self.subparsers = None
        self.default_subcommand = None
        self.argparser = self.create_argparser()
        self.last_invoke = None
        self.setup_args(self.argparser)

    def inject_context(self, parent, context):
        """ Map context attributes from the parent and from the context
        argument into this instance (as attributes). """
        self.context_keys = set(context.keys())
        for key, value in context.items():
            setattr(self, key, value)
        if parent:
            for key in parent.context_keys:
                setattr(self, key, getattr(parent, key))
            self.context_keys |= parent.context_keys

    def create_argparser(self):
        """ Factory for arg parser, can be replaced with any ArgParser compat
        instance. """
        Formatter = argparse.RawDescriptionHelpFormatter
        desc = self.clean_docstring()[1]
        parser = argparse.ArgumentParser(self.name, description=desc,
                                         formatter_class=Formatter)
        return parser

    def clean_docstring(self):
        """ Return sanitized docstring from this class.
        The first line of the docstring is the title, and remaining lines are
        the details, aka git style. """
        if not self.__doc__:
            raise SyntaxError('Docstring missing for: %s' % self)
        doc = [x.strip() for x in self.__doc__.splitlines()]
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
        completer functions must use set()s but this wrapper has to return a
        list to satisfy cmd.Cmd. """
        choices = self.complete(text, line, begin, end)
        debug.log("PREFORMAT CHOICES", choices)
        sz = len(choices)
        if sz == 1:
            return ['%s ' % shlex.quote(choices.pop())]
        elif sz > 2:
            # We don't need the sentinel choice to prevent completion
            # when there is already more than 1 choice.
            choices -= {completer.ActionCompleter.sentinel}
        return ['%s ' % x for x in choices]

    def complete(self, text, line, begin, end):
        """ Do naive argument parsing so the completer has better ability to
        understand expansion rules. """
        debug.log()
        import datetime
        debug.log(datetime.datetime.now())
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
                debug.log("CONSUME FOR POS", x_action, pos_args)
                x_action.consume(pos_args)
                if not x_action.reached_min:
                    choices = x_action(self, text)
                    break
                elif not x_action.full:
                    choices |= x_action(self, text)

        debug.log('line ::%s::' % line)
        debug.log("text ::%s::" % text)
        debug.log('args', args)
        debug.log('choices', choices)
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

    def invoke(self, args):
        """ If a subparser is present and configured  we forward invocation to
        the correct subcommand method. If all else fails we call run(). """
        commands = self.get_commands_from(args)
        self.last_invoke = time.time()
        if self.subparsers:
            try:
                command = commands[self.depth]
            except IndexError:
                if self.default_subcommand:
                    self.default_subcommand.argparser.parse_args([], namespace=args)
                    self.invoke(args)  # retry
                    return
            else:
                self.prerun(args)
                command.invoke(args)
                return
        self.prerun(args)
        self.run(args)

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

    def add_subcommand(self, command_class, default=False):
        command = command_class(parent=self)
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
        prog = '%s %s' % (self.subparsers._prog_prefix, command.name)
        if command.subparsers:
            for x in command.subparsers.choices.values():
                x.prog = '%s %s' % (prog, x.prog.rsplit(' ', 1)[1])
        command.argparser.prog = prog
        action = self.subparsers._ChoicesPseudoAction(command.name, (), help)
        self.subparsers._choices_actions.append(action)
        self.subparsers._name_parser_map[command.name] = command.argparser
        command.argparser.set_defaults(**{'command%d' % self.depth: command})
        self.subcommands.append(command)
