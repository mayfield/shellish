"""
Supplemental code for stdlib package(s).  Namely argparse.
"""

import argparse
import io
import os
import re
import shutil
import sys
import textwrap
import warnings
from .. import rendering, paging


class HelpSentinel(str):

    def __len__(self):
        return 1

HELP_SENTINEL = HelpSentinel()


class ShellishParser(argparse.ArgumentParser):

    env_desc = 'Environment variables can be used to set argument default ' \
               'values.  Note that they may still be overridden by ' \
               'supplying the argument on the command line.\n\nWhen an ' \
               'argument has a corresponding environment variable it is ' \
               'noted parenthetically to the right of the argument ' \
               'description.'

    def __init__(self, command, **kwargs):
        self._env_actions = {}
        self._command = command
        super().__init__(command.name, **kwargs)

    def bind_env(self, action, env):
        """ Bind an environment variable to an argument action.  The env
        value will traditionally be something uppercase like `MYAPP_FOO_ARG`.

        Note that the ENV value is assigned using `set_defaults()` and as such
        it will be overridden if the argument is set via `parse_args()` """
        if env in self._env_actions:
            raise ValueError('Duplicate ENV variable: %s' % env)
        self._env_actions[env] = action
        action.env = env

    def unbind_env(self, action):
        """ Unbind an environment variable from an argument action.  Only used
        when the subcommand hierarchy changes. """
        del self._env_actions[action.env]
        delattr(action, 'env')

    def parse_known_args(self, *args, **kwargs):
        env_defaults = {}
        for env, action in self._env_actions.items():
            if os.environ.get(env):
                env_defaults[action.dest] = os.environ[env]
                action.required = False  # XXX This is a hack
        if env_defaults:
            self.set_defaults(**env_defaults)
        return super().parse_known_args(*args, **kwargs)

    def _get_formatter(self):
        width = shutil.get_terminal_size()[0] - 2
        return self.formatter_class(prog=self.prog, width=width)

    def format_help(self):
        formatter = self._get_formatter()
        formatter.add_usage(self.usage, self._actions,
                            self._mutually_exclusive_groups)
        if self.description and '\n' in self.description:
            desc = self.description.split('\n\n', 1)
            if len(desc) == 2 and '\n' not in desc[0]:
                title, about = desc
            else:
                title, about = None, desc
        else:
            title, about = self.description, None
        if title:
            formatter.add_text('<b><u>%s</u></b>' % title)
        if about:
            formatter.add_text(about)
        if self._env_actions:
            formatter.start_section('<b>environment variables</b>')
            formatter.add_text(self.env_desc)
            formatter.end_section()

        for action_group in self._action_groups:
            formatter.start_section('<b>%s</b>' % action_group.title)
            formatter.add_text(action_group.description)
            formatter.add_arguments(action_group._group_actions)
            formatter.end_section()
        formatter.add_text(self.epilog)
        return formatter.format_help()

    def print_help(self, *args, **kwargs):
        """ Add pager support to help output. """
        if self._command.session.allow_pager:
            desc = 'Help\: %s' % '-'.join(self.prog.split())
            pager_kwargs = self._command.get_pager_spec()
            with paging.pager_redirect(desc, **pager_kwargs):
                return super().print_help(*args, **kwargs)
        else:
                return super().print_help(*args, **kwargs)

    def add_argument(self, *args, help=HELP_SENTINEL, **kwargs):
        return super().add_argument(*args, help=help, **kwargs)


class VTMLHelpFormatter(argparse.HelpFormatter):

    hardline = re.compile('\n\s*\n')

    def vtmlrender(self, string):
        vstr = rendering.vtmlrender(string)
        return str(vstr.plain() if not sys.stdout.isatty() else vstr)

    def start_section(self, heading):
        super().start_section(self.vtmlrender(heading))

    def _fill_text(self, text, width, indent):
        r""" Reflow text but preserve hardlines (\n\n). """
        paragraphs = self.hardline.split(str(self.vtmlrender(text)))
        return '\n\n'.join(textwrap.fill(x, width, initial_indent=indent,
                                         subsequent_indent=indent)
                           for x in paragraphs)

    def _get_help_string(self, action):
        """ Adopted from ArgumentDefaultsHelpFormatter. """
        help = action.help
        prefix = ''
        if getattr(action, 'env', None):
            prefix = '(<cyan>%s</cyan>) ' % action.env

        if '%(default)' not in help and \
           action.default not in (argparse.SUPPRESS, None):
            if action.option_strings and action.nargs != 0:
                if isinstance(action.default, io.IOBase):
                    default = action.default.name
                else:
                    default = action.default
                prefix = '[<b>%s</b>] %s ' % (default, prefix)
        vhelp = rendering.vtmlrender('%s<blue>%s</blue>' % (prefix, help))
        return str(vhelp.plain() if not sys.stdout.isatty() else vhelp)


class SafeFileContext(object):
    """ Used by SafeFileType to provide a file-like context manager. """

    def __init__(self, ft, filename):
        self.ft = ft
        self.filename = filename
        self.fd = None
        self.is_stdio = None
        self.used = False

    def __call__(self):
        warnings.warn("Calling the file argument is no longer required")
        return self

    def __enter__(self):
        assert not self.used
        self.used = True
        if self.filename == '-':
            self.is_stdio = True
            if 'r' in self.ft._mode:
                stdio = sys.stdin
            elif 'w' in self.ft._mode:
                stdio = sys.stdout
            else:
                raise ValueError("Invalid mode for stdio: %s" % self.ft._mode)
            self.fd = stdio
        else:
            self.is_stdio = False
            self.fd = open(self.filename, self.ft._mode, self.ft._bufsize,
                           self.ft._encoding, self.ft._errors)
        return self.fd

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.fd is not None:
            if self.is_stdio:
                self.fd.flush()
            else:
                self.fd.close()

    def __str__(self):
        """ Report the last string passed into our call.  This is our candidate
        filename but in practice it is THE filename used. """
        return str(self.filename)

    def __repr__(self):
        """ Report the last string passed into our call.  This is our candidate
        filename but in practice it is THE filename used. """
        return '<%s: %s>' % (type(self).__name__, repr(self.filename))


class SafeFileType(argparse.FileType):
    """ A side-effect free version of argparse.FileType that prevents erroneous
    creation of files when doing tab completion.  Arguments that use this type
    are given a factory function that will return a context manager for the
    underlying file. """

    def __call__(self, string):
        return SafeFileContext(self, string)
