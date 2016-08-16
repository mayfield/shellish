"""
Supplemental code for stdlib package(s).  Namely argparse.
"""

import argparse
import re
import shutil
import sys
import textwrap
import warnings
from .. import layout


class ShellishParser(argparse.ArgumentParser):

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
        for action_group in self._action_groups:
            formatter.start_section('<b>%s</b>' % action_group.title)
            formatter.add_text(action_group.description)
            formatter.add_arguments(action_group._group_actions)
            formatter.end_section()
        formatter.add_text(self.epilog)
        return formatter.format_help()


class VTMLHelpFormatter(argparse.HelpFormatter):

    hardline = re.compile('\n\s*\n')

    def vtmlrender(self, string):
        vstr = layout.vtmlrender(string)
        return str(vstr.plain() if not sys.stdout.isatty() else vstr)

    def start_section(self, heading):
        super().start_section(self.vtmlrender(heading))

    def _fill_text(self, text, width, indent):
        r""" Reflow text but preserve hardlines (\n\n). """
        paragraphs = self.hardline.split(str(self.vtmlrender(text)))
        return '\n\n'.join(textwrap.fill(x, width, initial_indent=indent,
                                         subsequent_indent=indent)
                           for x in paragraphs)


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
