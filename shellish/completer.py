"""
Tab completion handling.
"""

import argparse
import os

__public__ = []


class ActionCompleter(object):
    """ Stateful behavior for tab completion.  Calling this instance returns
    valid choices for the action. """

    sentinel = ' '

    def __init__(self, action):
        self.action = action
        self.key = None
        self.choices = None
        self.consumed = 0
        self.subparsers = None
        if action.choices and hasattr(action.choices, 'items'):
            self.subparsers = action.choices.copy()
        if action.option_strings:
            # Only include the longest option string under the assumption
            # that this most accurately describes the argument.
            self.key = max(action.option_strings, key=len)
        if action.choices:
            self.completer = self.choice_complete
            self.choices = action.choices
        elif getattr(action, 'complete', None):
            self.completer = self.proxy_complete(action.complete)
        else:
            self.completer = self.hint_complete
        self.parse_nargs(action.nargs)

    def __str__(self):
        return '<%s key:%s action:(%s)>' % (type(self).__name__, self.key,
               self.about_action())

    __repr__ = __str__

    def __call__(self, command, prefix, args):
        args = self.silent_parse_args(command, args)
        return self.completer(prefix, args)

    def silent_parse_args(self, command, args):
        """ Silently attempt to parse args.  If there is a failure then we
        ignore the effects.  Using an in-place namespace object ensures we
        capture as many of the valid arguments as possible when the argparse
        system would otherwise throw away the results. """
        args_ns = argparse.Namespace()
        stderr_save = argparse._sys.stderr
        argparse._sys.stderr = os.devnull
        try:
            command.argparser.parse_known_args(args, args_ns)
        except BaseException:
            pass
        finally:
            argparse._sys.stderr = stderr_save
        return args_ns

    def parse_nargs(self, nargs):
        """ Nargs is essentially a multi-type encoding.  We have to parse it
        to understand how many values this action may consume. """
        self.max_args = self.min_args = 0
        if nargs is None:
            self.max_args = self.min_args = 1
        elif nargs == argparse.OPTIONAL:
            self.max_args = 1
        elif nargs == argparse.ZERO_OR_MORE:
            self.max_args = None
        elif nargs in (argparse.ONE_OR_MORE, argparse.REMAINDER):
            self.min_args = 1
            self.max_args = None
        elif nargs != argparse.PARSER:
            self.max_args = self.min_args = nargs

    def consume(self, args):
        """ Consume the arguments we support.  The args are modified inline.
        The return value is the number of args eaten. """
        consumable = args[:self.max_args]
        self.consumed = len(consumable)
        del args[:self.consumed]
        return self.consumed

    @property
    def full(self):
        """ Can this action take more arguments? """
        if self.max_args is None:
            return False
        return self.consumed >= self.max_args

    @property
    def reached_min(self):
        """ Have we consumed the minimum number of args. """
        return self.consumed >= self.min_args

    def about_action(self):
        """ Simple string describing the action. """
        name = self.action.metavar or self.action.dest
        type_name = self.action.type.__name__ if self.action.type else ''
        if self.action.help or type_name:
            extra = ' (%s)' % (self.action.help or 'type: %s' % type_name)
        else:
            extra = ''
        return name + extra

    def choice_complete(self, prefix, args):
        return frozenset(x for x in self.choices if x.startswith(prefix))

    def hint_complete(self, prefix, args):
        """ For arguments that don't have complete functions or .choices we
        can only hint about the argument details. The results are designed to
        not self-expand (ie, len(choices) > 1). """
        return frozenset(('[%s]' % self.about_action(), self.sentinel))

    def proxy_complete(self, func):
        """ Pass completion work to foreign function. """
        return lambda *args, **kwargs: frozenset(func(*args, **kwargs))
