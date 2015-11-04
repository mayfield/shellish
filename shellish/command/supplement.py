"""
Supplemental code for stdlib package(s).  Namely argparse.
"""

import argparse
import re
import shutil
import sys
import textwrap
from .. import layout


class ShellishParser(argparse.ArgumentParser):

    def _get_formatter(self):
        width = shutil.get_terminal_size()[0] - 2
        return self.formatter_class(prog=self.prog, width=width)

    def format_help(self):
        formatter = self._get_formatter()
        formatter.add_usage(self.usage, self._actions,
                            self._mutually_exclusive_groups)
        if '\n' in self.description:
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


class SafeFileType(argparse.FileType):
    """ A side-effect free version of argparse.FileType that prevents erroneous
    creation of files when doing tab completion.  Arguments that use this
    type are given a factory function that will return the file asked for by
    the user instead of an open file handle. """

    def __call__(self, string):
        if string == '-':
            if 'r' in self._mode:
                return lambda: sys.stdin
            elif 'w' in self._mode:
                return lambda: sys.stdout
            else:
                raise ValueError("Invalid mode for stdio: %s" % self._mode)
        return lambda: open(string, self._mode, self._bufsize, self._encoding,
                            self._errors)
