"""
Supplemental code for stdlib package(s).  Namely argparse.
"""

import argparse
import io
import os
import re
import shutil
import sys
import warnings
from .. import paging, layout
from ..rendering import vtmlrender, VTMLBuffer


class HelpSentinel(str):

    def __len__(self):
        return 1

HELP_SENTINEL = HelpSentinel()
NBSP = ' '  # U+00A0


class ShellishHelpFormatter(argparse.HelpFormatter):

    leadingws = re.compile('^\s+')
    whitespace = re.compile('[ \n\t\v\f\r]+')
    max_width = 100

    class _Section(argparse.HelpFormatter._Section):

        def format_help(self):
            if self.parent is not None:
                self.formatter._indent()
            join = self.formatter._join_parts
            item_help = join([func(*args) for func, args in self.items])
            if self.parent is not None:
                self.formatter._dedent()
            if not item_help:
                return ''
            if self.heading in (argparse.SUPPRESS, None):
                heading_bar = ''
                return item_help
            else:
                current_indent = self.formatter._current_indent
                heading = '%*s%s' % (current_indent, '', self.heading.upper())
                heading_bar = vtmlrender('\n<u>%s</u>:\n\n' % heading)
            return join([heading_bar, item_help])

    def __init__(self, prog, max_width=None, width=None, **kwargs):
        if width is None:
            if max_width is None:
                max_width = self.max_width
            width = min(shutil.get_terminal_size()[0] - 2, max_width)
        super().__init__(prog, width=width, **kwargs)

    def format_help(self):
        return self._root_section.format_help()

    def _fill_text(self, text, width=None, indent=None):
        """ Reflow text width while maintaining certain formatting
        characteristics like double newlines and indented statements. """
        assert isinstance(text, str)
        if indent is None:
            indent = NBSP * self._current_indent
        assert isinstance(indent, str)
        paragraphs = []
        line_buf = []
        pre = ''
        for fragment in text.splitlines():
            pre_indent = self.leadingws.match(fragment)
            if not fragment or pre_indent:
                if line_buf:
                    line = ' '.join(line_buf)
                    paragraphs.append((pre, self.whitespace.sub(' ', line)))
                if not fragment:
                    paragraphs.append(('', ''))
                else:
                    pre = pre_indent.group()
                    fragment = self.leadingws.sub('', fragment)
                    paragraphs.append((pre, fragment))
                line_buf = []
                pre = ''
            else:
                line_buf.append(fragment)
        if line_buf:
            line = ' '.join(line_buf)
            paragraphs.append((pre, self.whitespace.sub(' ', line)))
        indent = VTMLBuffer(indent)
        nl = VTMLBuffer('\n')
        if width is None:
            width = self._width - len(indent)
        lines = []
        for pre, paragraph in paragraphs:
            pwidth = width - len(pre)
            lines.append(nl.join((indent + pre + x)
                         for x in vtmlrender(paragraph).wrap(pwidth)))
        return nl.join(lines)

    def _format_text(self, text):
        if '%(prog)' in text:
            text = text % dict(prog=self._prog)
        return self._fill_text(text) + '\n\n'

    def _get_help_string(self, action):
        """ Adopted from ArgumentDefaultsHelpFormatter. """
        raise NotImplementedError('')

    def _format_usage(self, *args, **kwargs):
        usage = super()._format_usage(*args, **kwargs)
        return VTMLBuffer('\n').join(vtmlrender('<red>%s</red>' % x)
                                     for x in usage.split('\n'))

    def _join_parts(self, parts):
        return VTMLBuffer('').join(x for x in parts
                                   if x not in (None, argparse.SUPPRESS))

    def _get_type_label(self, typeattr):
        if isinstance(typeattr, argparse.FileType) or typeattr is open:
            return 'file'
        if hasattr(typeattr, '__name__'):
            name = typeattr.__name__
            if name != '<lambda>':
                return name

    def _get_default_metavar_for_optional(self, action):
        if action.type is None:
            return 'STR'
        label = self._get_type_label(action.type)
        if label is not None:
            return label.upper()
        return 'VALUE'

    def _get_default_metavar_for_positional(self, action):
        if action.dest is argparse.SUPPRESS:
            if isinstance(action, argparse._SubParsersAction):
                return action.metavar or 'SUBCOMMAND'
            else:
                raise RuntimeError("Can not produce metavar for: %r" % action)
        return action.dest.upper()

    def _format_action_invocation(self, action):
        args = None
        if not action.option_strings:  # positional
            if action.metavar is None:
                options = [self._get_default_metavar_for_positional(action)]
            elif action.metavar is not argparse.SUPPRESS:
                options = [action.metavar]
            else:
                raise NotImplementedError()
        else:
            options = action.option_strings
            if action.nargs != 0:
                metavar = self._get_default_metavar_for_optional(action)
                args = self._format_args(action, metavar)
        res = ', '.join('<b><blue>%s</blue></b>' % x for x in options)
        return ' '.join((res, args)) if args else res

    def _metavar_formatter(self, action, default_metavar):
        if action.metavar is not None:
            result = action.metavar
        else:
            result = default_metavar

        def format(tuple_size):
            if isinstance(result, tuple):
                return result
            else:
                return (result, ) * tuple_size
        return format

    def _format_action_table(self, action, terse=False):
        indent = NBSP * self._current_indent
        pad = NBSP * 2
        is_subparser = isinstance(action, argparse._SubParsersAction)
        if is_subparser:
            sub_name = self._get_default_metavar_for_positional(action)
            left_col = ["<b>%s</b>" % sub_name]
        else:
            left_col = [self._format_action_invocation(action)]
        if action.required:
            left_col[-1] += ' <b><i>(required)</i></b>'
        if action.default not in (argparse.SUPPRESS, None) and \
           action.nargs != 0:
            if isinstance(action.default, io.IOBase):
                default = action.default.name
            else:
                default = action.default
            left_col.append(pad + 'default: <b>%s</b>' % (default,))
        if not terse and not is_subparser:
            if isinstance(action.nargs, int):
                arg_count = action.nargs
            else:
                arg_count = {
                    argparse.OPTIONAL: 'optional',
                    argparse.ZERO_OR_MORE: 'zero or more',
                    argparse.ONE_OR_MORE: 'one or more',
                    argparse.REMAINDER: 'remainder',
                }.get(action.nargs)
            if arg_count:
                left_col.append(pad + 'count: <b>%s</b>' % arg_count)
            label = self._get_type_label(action.type)
            if label:
                left_col.append(pad + 'type: <b>%s</b>' % label)
            if action.choices:
                if len(action.choices) < 5:
                    choices = ', '.join('<b>%s</b>' % x
                                        for x in action.choices)
                    left_col.append(pad + 'choices: {%s}' % choices)
                else:
                    left_col.append(pad + 'choices:')
                    for x in action.choices:
                        left_col.append((pad * 3) + '<b>%s</b>' % x)
            if getattr(action, 'env', None):
                left_col.append(pad + 'env: <b>%s</b>' % action.env)
        left_col = [indent + x for x in left_col]
        # Perform optional substitutions on help text.
        if action.help and action.help is not HELP_SENTINEL:
            params = dict(vars(action), prog=self._prog)
            for name in list(params):
                if params[name] is argparse.SUPPRESS:
                    del params[name]
            for name in list(params):
                if hasattr(params[name], '__name__'):
                    params[name] = params[name].__name__
            if params.get('choices') is not None:
                choices_str = ', '.join([str(c) for c in params['choices']])
                params['choices'] = choices_str
            help_text = action.help % params
        else:
            help_text = ''
        feed = [('\n'.join(left_col), help_text)]
        for subaction in self._iter_indented_subactions(action):
            feed.extend(self._format_action_table(subaction, terse=True))
        return feed

    def add_table(self, actions):
        table_output = io.StringIO()
        table_output.isatty = sys.stdout.isatty
        config = {
            "width": self._width,
            "justify": True,
            "overflow": 'wrap',
            "columns": [{
                "padding": 2,
                "overflow": 'preformatted'
            }, {
                "padding": 4
            }]
        }
        table = layout.Table(file=table_output, **config)
        rows = []
        for action in actions:
            if action.help is argparse.SUPPRESS:
                continue
            rows.extend(self._format_action_table(action))

        def render(data):
            table.print(data)
            table.close()
            return table_output.getvalue()
        if rows:
            self._add_item(render, [rows])


class ShellishParser(argparse.ArgumentParser):

    HelpFormatter = ShellishHelpFormatter

    def __init__(self, *args, command=None, formatter_class=None, **kwargs):
        self._env_actions = {}
        self._command = command
        if formatter_class is None:
            formatter_class = self.HelpFormatter
        super().__init__(*args, formatter_class=formatter_class, **kwargs)

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

    def format_help(self):
        formatter = self._get_formatter()
        formatter.add_usage(self.usage, self._actions,
                            self._mutually_exclusive_groups)
        if self.description and '\n' in self.description:
            desc = self.description.split('\n\n', 1)
            if len(desc) == 2 and '\n' not in desc[0]:
                title, about = desc
            else:
                title, about = '', desc
        else:
            title, about = self.description, ''
        if title and title.strip():
            formatter.add_text('<b><u>%s</u></b>\n' % title.strip())
        if about and about.rstrip():
            formatter.add_text(about.rstrip())
        for group in self._action_groups:
            formatter.start_section(group.title)
            formatter.add_text(group.description)
            formatter.add_table(actions=group._group_actions)
            formatter.end_section()
        formatter.add_text(self.epilog)
        return formatter.format_help()

    def print_help(self, *args, **kwargs):
        """ Add pager support to help output. """
        if self._command is not None and self._command.session.allow_pager:
            desc = 'Help\: %s' % '-'.join(self.prog.split())
            pager_kwargs = self._command.get_pager_spec()
            with paging.pager_redirect(desc, **pager_kwargs):
                return super().print_help(*args, **kwargs)
        else:
                return super().print_help(*args, **kwargs)

    def _print_message(self, message, file=None):
        if not message:
            return
        if file is None:
            file = sys.stderr
        if isinstance(message, VTMLBuffer) and not file.isatty():
            message = message.plain()
        file.write(str(message))

    def add_argument(self, *args, help=HELP_SENTINEL, **kwargs):
        return super().add_argument(*args, help=help, **kwargs)

    def add_subparsers(self, prog=None, **kwargs):
        """ Supplement a proper `prog` keyword argument for the subprocessor.
        The superclass technique for getting the `prog` value breaks because
        of our VT100 escape codes injected by `format_help`. """
        if prog is None:
            # Use a non-shellish help formatter to avoid vt100 codes.
            f = argparse.HelpFormatter(prog=self.prog)
            f.add_usage(self.usage, self._get_positional_actions(),
                        self._mutually_exclusive_groups, '')
            prog = f.format_help().strip()
        return super().add_subparsers(prog=prog, **kwargs)

    def _get_positional_kwargs(self, dest, **kwargs):
        dest = dest.replace('-', '_')
        return super()._get_positional_kwargs(dest, **kwargs)


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
