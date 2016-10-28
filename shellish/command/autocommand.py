"""
A command class that is built from a normal function.
"""

import argparse
import inspect
from . import command


class AutoCommand(command.Command):
    """ Auto command ABC.  This command wraps a generic function and tries
    to map the function signature to a parser configuration.  Use the
    @autocommand decorator to use it. """

    falsy = {
        'false',
        'none',
        'null',
        '0',
        'no',
        'off',
        'disable'
    }

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
                if options['type'] is bool:
                    if label == 'keyword':
                        options['action'] = 'store_%s' % \
                            str(not param.default).lower()
                        del options['type']
                    else:
                        options['type'] = lambda x: x.lower() not in self.falsy
                else:
                    try:
                        options['metavar'] = options['type'].__name__.upper()
                    except:
                        pass
            action = parser.add_argument(name.replace('_', '-'), **options)
            action.label = label


def autocommand(func):
    """ A simplified decorator for making a single function a Command
    instance.  In the future this will leverage PEP0484 to do really smart
    function parsing and conversion to argparse actions. """
    name = func.__name__
    title, desc = command.parse_docstring(func)
    if not title:
        title = 'Auto command for: %s' % name
    if not desc:
        # Prevent Command from using docstring of AutoCommand
        desc = ' '
    return AutoCommand(title=title, desc=desc, name=name, func=func)
