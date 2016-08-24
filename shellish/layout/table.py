"""
Table layout.
"""

import collections
import csv
import inspect
import itertools
import json
import math
import operator
import re
import shutil
import sys
import time
from .. import rendering


class RowsNotFound(ValueError):
    """ Similar to StopIteration but not specific to iterator protocol. """
    pass


class Table(object):
    """ A visual layout for row oriented data (like csv).  Most of the code
    here is dedicated to fitting the data as losslessly as possible onto a
    terminal screen.  The basic design goal is to fit your rows onto the
    screen without overflowing;  However a table instance can be configured
    to overflow if desired (clip=False).  For detailed help on using this
    class, see the __init__ method, or use the helper function tabulate() for
    simple use cases.

    This class is also a context manager which is applicable for printing
    streams of data or when combined with output formats that require closing
    tags. """

    column_padding = 2
    column_align = 'left'  # {left,right,center}
    title_align = 'left'
    cliptext = rendering.beststr('…', '...')
    column_minwidth = len(cliptext)
    renderer_types = {}

    # You probably shouldn't mess with these unless you really need custom
    # rendering performance.  Chances are you really don't and should
    # manage your data stream more carefully first.
    min_render_prefill = 5
    max_render_prefill = 200
    max_render_delay = 2

    def __init__(self, columns=None, headers=None, accessors=None, width=None,
                 clip=None, flex=True, file=None, cliptext=None,
                 column_minwidth=None, column_padding=None, column_align=None,
                 renderer=None, title=None, title_align=None, column_mask=None,
                 hide_header=False, hide_footer=False):
        """ The .columns should be a list of width specs or a style dict.
        Width specs can be whole numbers representing fixed char widths,
        fractions representing percentages of available table width or None
        if the column is unspec'd.  Unspec'd columns are then calculated at
        render time according to the .flex setting.  If not provided then all
        columns will be unspec'd.  E.g.

            >>> t = Table(columns=[
                25, # fixed width, 25 chars
                50, # fixed width, 50 chars
                0.33, # 33% percent of total available space
                None, # if flex=True will size to row content
                None  # if flex=False will split remainder
            ])

        The columns style dict supports the following properties:

            "width":    Follows the aforementioned column width definition.
            "minwidth": Minimum characters a column can be shrunken to.
            "padding":  Property for custom padding of individual columns.
                        Whole number of white space characters to add.
            "align":    How to justify the contents of the column. Valid
                        choices are 'left', 'right', and 'center'.

            E.g.

            >>> t = Table(columns=[{
                "width": 1/4,
                "padding": 4,
                "align": "right"
            }, {
                "width": 1/4,
                "padding": 0,
                "align": "center"
            }, {
                "padding": 0
            }])

        When any values are omitted from the column def they will pickup
        default settings from the table wide .column_padding, .column_align
        and .column_minwidth attributes respectively.

        The .headers arg should contain a list of strings to display on the
        first line or be unset to skip the header line.

        The .accessors argument is to be used in conjunction with datasets
        are not 1:1 conforming lists.  Typically this means the data is some
        other type like a dictionary or an object.  The accessors list should
        be a list of strings (dictionary keys) or functions that can return
        the correct datum for each column respectively. E.g.

            >>> t = Table(headers=['First', 'Second', 'Last'],
                          accessors=['one', 'two', 'three'])
            >>> t.print_row({"three": "333", "one": "1", "two": "22"})

        If .flex is turned on and you have unspec columns (None) the render
        method will scan your initial data stream to determine the best widths
        to use.  It is permissible to submit your entire data set at this
        point if you have enough memory.

        By default the columns will clip text that overflows; Set .clip to
        False to disable this behavior but be warned the table will not look
        good. """
        self.title = title
        # Freeze the table definitions...
        try:
            self.columns_def = columns.copy() if columns is not None else None
        except AttributeError:
            self.columns_def = tuple(columns)
        self.accessors_def = tuple(accessors or ())
        self.headers = tuple(headers or ())
        self.width = width
        self.flex = flex
        self.file = file if file is not None else sys.stdout
        self.hide_header = hide_header
        self.hide_footer = hide_footer
        self.column_mask = column_mask
        self.default_renderer = None
        if not renderer:
            if not self.file.isatty():
                renderer = 'plain'
            else:
                renderer = 'terminal'
        self.renderer_class = self.lookup_renderer(renderer)
        self.clip = clip
        if cliptext is not None:
            self.cliptext = cliptext
        if column_padding is not None:
            self.column_padding = column_padding
        if column_minwidth is not None:
            self.column_minwidth = column_minwidth
        if column_align is not None:
            self.column_align = column_align
        if title_align is not None:
            self.title_align = title_align

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return self.close(exception=exc)

    def close(self, exception=None):
        if self.default_renderer:
            self.default_renderer.close(exception=exception)

    def lookup_renderer(self, name):
        return self.renderer_types[name]

    @classmethod
    def register_renderer(cls, renderer):
        cls.renderer_types[renderer.name] = renderer

    @classmethod
    def unregister_renderer(cls, renderer):
        del cls.renderer_types[renderer.name]

    @classmethod
    def attach_arguments(cls, parser, prefix='--', skip_formats=False,
                         format_excludes=None, format_title=None,
                         format_desc=None, skip_render=False,
                         render_excludes=None, render_title=None,
                         render_desc=None, skip_filters=False,
                         filter_excludes=None, filter_title=None,
                         filter_desc=None):
        """ Attach argparse arguments to an argparse parser/group with table
        options.  These are renderer options and filtering options with the
        ability to turn off headers and footers.  The return value is function
        that parses an argparse.Namespace object into keyword arguments for a
        layout.Table constructor. """
        convs = []
        if not skip_formats:
            attach = cls.attach_format_arguments
            convs.append(attach(parser, prefix, format_excludes, format_title,
                                format_desc))
        if not skip_render:
            attach = cls.attach_render_arguments
            convs.append(attach(parser, prefix, render_excludes, render_title,
                                render_desc))
        if not skip_filters:
            attach = cls.attach_filter_arguments
            convs.append(attach(parser, prefix, filter_excludes, filter_title,
                                filter_desc))

        def argparse_ns_to_table_opts(ns):
            options = {}
            for conv in convs:
                options.update(conv(ns))
            return options
        return argparse_ns_to_table_opts

    @classmethod
    def attach_render_arguments(cls, parser, prefix='--', excludes=None,
                                title=None, desc=None):
        excludes = excludes or set()
        title = 'table render settings' if title is None else title
        desc = 'Overrides for table render settings.' if desc is None else desc
        group = parser.add_argument_group(title, description=desc)
        if 'no_clip' not in excludes:
            group.add_argument('--no-clip', action='store_true',
                               help='Do not clip the table output to fit the '
                               'screen.')
        if 'table_width' not in excludes:
            group.add_argument('--table-width', type=int, metavar='COLS',
                               help='Specify the table width in columns.')
        if 'table_padding' not in excludes:
            group.add_argument('--table-padding', type=int, metavar='COLS',
                               help='Specify whitespace padding for each '
                               'table column in characters.')
        if 'table_align' not in excludes:
            group.add_argument('--table-align', metavar='JUSTIFY',
                               choices={'left', 'center', 'right'},
                               help='Table column justification.')

        def ns2table(ns):
            opts = {}
            if ns.no_clip:
                opts['clip'] = False
            if ns.table_width is not None:
                opts['width'] = ns.table_width
            if ns.table_padding is not None:
                opts['column_padding'] = ns.table_padding
            if ns.table_align:
                opts['column_align'] = ns.table_align
            return opts
        return ns2table

    @classmethod
    def attach_format_arguments(cls, parser, prefix='--', excludes=None,
                                title=None, desc=None):
        excludes = excludes or set()
        title = 'table output format' if title is None else title
        desc = 'Selection of output formats for table display.  The ' \
               'default behavior is to detect the output device\'s ' \
               'capabilities.' if desc is None else desc
        group = parser.add_argument_group(title, description=desc)
        ex_group = group.add_mutually_exclusive_group()
        for name, renderer in sorted(cls.renderer_types.items()):
            if name in excludes:
                continue
            ex_group.add_argument('%s%s' % (prefix, name), dest='table_format',
                                  action='store_const', const=name,
                                  help=inspect.getdoc(renderer))

        def ns2table(ns):
            return {
                "renderer": ns.table_format,
            }
        return ns2table

    @classmethod
    def attach_filter_arguments(cls, parser, prefix='--', excludes=None,
                                title=None, desc=None):
        title = 'table filters' if title is None else title
        desc = 'Options for filtering the table display.' if desc is None \
               else desc
        group = parser.add_argument_group(title, description=desc)
        excludes = excludes or set()
        if 'columns' not in excludes:
            group.add_argument('%scolumns' % prefix, dest='table_columns',
                               metavar="COL_INDEX", nargs='+', type=int,
                               help="Only show specific columns.")
        if 'no-header' not in excludes:
            group.add_argument('%sno-header' % prefix, dest='no_table_header',
                               action='store_true', help="Hide table header.")
        if 'no-footer' not in excludes:
            group.add_argument('%sno-footer' % prefix, dest='no_table_footer',
                               action='store_true', help="Hide table footer.")

        def ns2table(ns):
            return {
                "column_mask": ns.table_columns,
                "hide_header": ns.no_table_header,
                "hide_footer": ns.no_table_footer
            }
        return ns2table

    def make_accessors(self, columns):
        """ Accessors can be numeric keys for sequence row data, string keys
        for mapping row data, or a callable function.  For numeric and string
        accessors they can be inside a 2 element tuple where the 2nd value is
        the default value;  Similar to dict.get(lookup, default). """
        accessors = list(self.accessors_def or range(columns))
        for i, x in enumerate(accessors):
            if not callable(x):
                if isinstance(x, collections.abc.Sequence) and \
                   not isinstance(x, str):
                    key, default = x
                else:
                    key = x
                    default = ''

                def acc(row, key=key, default=default):
                    try:
                        return row[key]
                    except (KeyError, IndexError):
                        return default
                accessors[i] = acc
        return accessors

    def create_colspec(self, columns):
        """ Produce a full format columns spec dictionary.  The overrides spec
        can be a partial columns spec as described in the __init__ method's
        depiction of the .columns attribute. """
        spec = [{
            "width": None,
            "minwidth": self.column_minwidth,
            "padding": self.column_padding,
            "align": self.column_align
        } for x in range(columns)]
        if self.columns_def:
            for dst, src in zip(spec, self.columns_def):
                if hasattr(src, 'items'):
                    dst.update(src)
                else:
                    dst['width'] = src
        return spec

    def column_mask_filter(self, items):
        if not self.column_mask:
            return items
        else:
            return [x for i, x in enumerate(items, 1) if i in self.column_mask]

    def make_renderer(self, data=None):
        """ Consume and analyze everything we know up to this point and create
        a renderer instance that can be used for writing rows hence forth. """
        columns = (self.columns_def and len(self.columns_def)) or \
                  (self.headers and len(self.headers)) or \
                  (self.accessors_def and len(self.accessors_def))
        if not columns:
            if data:  # only a maybe since iterators are truthy
                # Peek into the data stream as a last resort.
                tmp_iter = iter(data)
                try:
                    peek = next(tmp_iter)
                except StopIteration:
                    pass
                else:
                    columns = len(peek)
                    data = itertools.chain([peek], tmp_iter)
            if not columns:
                raise RowsNotFound()
        accessors = self.column_mask_filter(self.make_accessors(columns))
        colspec = self.column_mask_filter(self.create_colspec(columns))
        headers = self.headers and self.column_mask_filter(self.headers[:])
        return self.renderer_class(colspec, accessors, headers, self, data)

    def print(self, rows):
        """ Write the data to our output stream (stdout).  If the table is not
        rendered yet, we will make a renderer instance which will freeze
        state. """
        row_iter = iter(rows)
        if not self.default_renderer:
            self.default_renderer = self.make_renderer(row_iter)
        self.default_renderer.print(row_iter)

    def print_row(self, row):
        return self.print([row])

    def print_footer(self, content):
        if self.hide_footer:
            return
        if not self.default_renderer:
            self.print([])
        self.default_renderer.print_footer(content)


class TableRenderer(object):
    """ A bundle of state for a particular table rendering job.  Each time a
    table is to be printed to a file or the screen a new instance of this
    object will be used to provide closure on the column spec and so forth.
    This is essentially frozen state computed from a table instance's
    definition. """

    name = None
    clip_default = False
    linebreak = rendering.beststr('—', '-')

    def __init__(self, colspec=None, accessors=None, headers=None, table=None,
                 seed=None):
        """ All calculated values required for rendering a table are kept
        here.  In theory a single Table instance can be used to render
        multiple and differing datasets in a concurrent system.  Admittedly
        this is over-engineered for a CLI suite and the result of a lazy
        Sunday. """
        self.colspec = colspec
        self.accessors = accessors
        self.headers = headers
        self.capture_table_state(table)
        self.prerendered = None
        self.seed = None
        if seed:
            self.prerendered, self.seed = self.seed_collect(seed)
        self.widths = self.calc_widths(self.prerendered)
        self.formatters = self.make_formatters()
        self.headers_drawn = not headers
        self.footers_drawn = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close(exception=exc)

    def close(self, exception=None):
        pass

    def seed_collect(self, seed):
        """ Collect values from the seed iterator as long as we can.  If the
        data stream is very large or taking too long we'll stop so the UI can
        render.  The goal is to reduce render latency but give the calc_widths
        routine as much data as we can reasonably afford to. """
        minfill = self.min_render_prefill
        maxfill = self.max_render_prefill
        maxtime = self.max_render_delay
        seed_iter = iter(seed)
        start = time.monotonic()

        def constrained_feed():
            for i, x in enumerate(seed_iter):
                yield x
                if i < minfill:
                    continue
                if i > maxfill or (time.monotonic() - start) >= maxtime:
                    return
        return list(self.render_data(constrained_feed())), seed_iter

    def print_header(self):
        """ Should write and flush output to a screen or file. """
        raise NotImplementedError("Subclass impl required")

    def cell_format(self, value):
        """ Subclasses should put any visual formatting specific to their
        rendering type here. """
        return rendering.vtmlrender(value)

    def get_overflower(self, width):
        return operator.methodcaller('clip', width, self.cliptext)

    def get_aligner(self, alignment, width):
        align_funcs = {
            "left": 'ljust',
            "right": 'rjust',
            "center": 'center'
        }
        return operator.methodcaller(align_funcs[alignment], width)

    def capture_table_state(self, table):
        """ Capture state from the table instance and store locally for safe
        keeping.  This is not specifically required but helps in keeping with
        our pseudo "frozen" nature. """
        for x in ('file', 'clip', 'cliptext', 'flex', 'width', 'title',
                  'title_align', 'max_render_prefill', 'max_render_delay',
                  'min_render_prefill', 'column_mask', 'hide_header'):
            setattr(self, x, getattr(table, x))
        if self.width is None:
            self.width = shutil.get_terminal_size()[0] \
                         if self.file is sys.stdout else 80
        if self.clip is None:
            self.clip = self.clip_default

    def render_data(self, data):
        """ Get the data from the raw list of objects. """
        if self.prerendered:
            for x in self.prerendered:
                yield x
            self.prerendered = None
        if self.seed:
            data = itertools.chain(self.seed, data)
            self.seed = None
        for obj in data:
            yield [self.cell_format(access(obj)) for access in self.accessors]

    def format_row(self, items):
        """ Apply overflow, justification and padding to a row. """
        return [formatter(x) for x, formatter in zip(items, self.formatters)]

    def format_fullwidth(self, value):
        """ Return a full width column. Note that the padding is inherited
        from the first cell which inherits from column_padding. """
        if not isinstance(value, rendering.VTML):
            value = rendering.VTML(value or '')
        pad = self.colspec[0]['padding']
        fmt = self.make_formatter(self.width - pad, pad, self.title_align)
        return fmt(value)

    def print_rendered(self, rendered_values):
        """ Format and print the pre-rendered data to the output device. """
        for row in rendered_values:
            print(*self.format_row(row), sep='', file=self.file)

    def print(self, data):
        if not self.headers_drawn:
            if not self.hide_header:
                self.print_header()
            self.headers_drawn = True
        self.print_rendered(self.render_data(data))

    def make_formatter(self, width, padding, alignment):
        """ Create formatter function that factors the width and alignment
        settings. """
        overflow = self.get_overflower(width) if self.clip else lambda x: x
        align = self.get_aligner(alignment, width)
        pad = self.get_aligner('center', width + padding)

        def fn(x, overflow=overflow, align=align, pad=pad):
            return pad(align(overflow(x)))
        return fn

    def make_formatters(self):
        """ Create a list formatter functions for each column.  They can then
        be stored in the render spec for faster justification processing. """
        return [self.make_formatter(inner_w, spec['padding'], spec['align'])
                for spec, inner_w in zip(self.colspec, self.widths)]

    def uniform_dist(self, spread, total):
        """ Produce a uniform distribution of `total` across a list of
        `spread` size. The result is non-random and uniform. """
        fraction, fixed_increment = math.modf(total / spread)
        fixed_increment = int(fixed_increment)
        balance = 0
        dist = []
        for _ in range(spread):
            balance += fraction
            withdrawl = 1 if balance > 0.5 else 0
            if withdrawl:
                balance -= withdrawl
            dist.append(fixed_increment + withdrawl)
        return dist

    def calc_widths(self, sample_data):
        """ Convert the colspec into absolute col widths. The sample data
        should be already rendered if used in conjunction with a Table. """
        usable_width = self.width
        usable_width -= sum(x['padding'] for x in self.colspec)
        spec = [x['width'] for x in self.colspec]
        remaining = usable_width
        unspec = []
        for i, x in enumerate(spec):
            if x is None:
                unspec.append(i)
            elif x > 0 and x < 1:
                spec[i] = w = math.floor(x * usable_width)
                remaining -= w
            else:
                remaining -= x
        if unspec:
            if self.flex and sample_data:
                for i, w in self.calc_flex(sample_data, remaining, unspec):
                    spec[i] = w
            else:
                dist = self.uniform_dist(len(unspec), remaining)
                for i, width in zip(unspec, dist):
                    spec[i] = width
        return spec

    def calc_flex(self, data, max_width, cols):
        """ Scan the entire data source returning the best width for each
        column given the width constraint.  If some columns will clip we
        calculate the best concession widths. """
        colstats = []
        for i in cols:
            lengths = [len(x[i]) for x in data]
            if self.headers:
                lengths.append(len(self.headers[i]))
            lengths.append(self.colspec[i]['minwidth'])
            counts = collections.Counter(lengths)
            colstats.append({
                "column": i,
                "counts": counts,
                "offt": max(lengths),
                "chop_mass": 0,
                "chop_count": 0,
                "total_mass": sum(a * b for a, b in counts.items())
            })
        if self.clip:
            self.adjust_clipping(max_width, colstats)
        required = sum(x['offt'] for x in colstats)
        if required < max_width:
            # Fill remaining space proportionately.
            remaining = max_width
            for x in colstats:
                x['offt'] = math.floor((x['offt'] / required) * max_width)
                remaining -= x['offt']
            if remaining:
                dist = self.uniform_dist(len(cols), remaining)
                for adj, col in zip(dist, colstats):
                    col['offt'] += adj
        return [(x['column'], x['offt']) for x in colstats]

    def adjust_clipping(self, max_width, colstats):
        """ Clip the columns based on the least negative affect it will have
        on the viewing experience.  We take note of the total character mass
        that will be clipped when each column should be narrowed.  The actual
        score for clipping is based on percentage of total character mass,
        which is the total number of characters in the column. """
        next_score = lambda x: (x['counts'][x['offt']] + x['chop_mass'] +
                                x['chop_count']) / x['total_mass']
        cur_width = lambda: sum(x['offt'] for x in colstats)
        min_width = lambda x: self.colspec[x['column']]['minwidth']
        while cur_width() > max_width:
            nextaffects = [(next_score(x), i) for i, x in enumerate(colstats)
                           if x['offt'] > min_width(x)]
            if not nextaffects:
                break  # All columns are as small as they can get.
            nextaffects.sort()
            chop = colstats[nextaffects[0][1]]
            chop['chop_count'] += chop['counts'][chop['offt']]
            chop['chop_mass'] += chop['chop_count']
            chop['offt'] -= 1


class PlainTableRenderer(TableRenderer):
    """ Render output without any special formatting. """

    name = 'plain'

    def print_header(self):
        headers = [rendering.VTML(x or '') for x in self.headers]
        header = ''.join(map(str, self.format_row(headers)))
        if self.title:
            print(self.format_fullwidth(self.title), file=self.file)
        print(header, file=self.file)
        print(self.linebreak * len(header), file=self.file)

    def print_footer(self, content):
        row = self.format_fullwidth(content)
        if not self.footers_drawn:
            self.footers_drawn = True
            print(self.linebreak * len(row), file=self.file)
        print(row, file=self.file)

    def cell_format(self, value):
        return rendering.vtmlrender(value, plain=True)

Table.register_renderer(PlainTableRenderer)


class TerminalTableRenderer(TableRenderer):
    """ Render a table designed to fit/fill a terminal.  This renderer produces
    the most human friendly output when on a terminal device. """

    name = 'terminal'
    clip_default = True
    title_format = '\n<b>%s</b>\n'
    header_format = '<reverse>%s</reverse>'
    footer_format = '<dim>%s</dim>'

    def print_header(self):
        headers = [rendering.VTML(x or '') for x in self.headers]
        header = ''.join(map(str, self.format_row(headers)))
        if self.title:
            title = self.format_fullwidth(self.title)
            rendering.vtmlprint(self.title_format % title, file=self.file)
        rendering.vtmlprint(self.header_format % header, file=self.file)

    def print_footer(self, content):
        row = self.format_fullwidth(content)
        if not self.footers_drawn:
            self.footers_drawn = True
            print(self.linebreak * len(row), file=self.file)
        rendering.vtmlprint(self.footer_format % row, file=self.file)

Table.register_renderer(TerminalTableRenderer)


class JSONTableRenderer(TableRenderer):
    """ Generate JSON output of the table. """

    name = 'json'
    key_split = re.compile('[\s\-_\.\/]')
    key_filter = re.compile('[^a-zA-Z0-9]')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen_keys = set()
        self.keys = []
        self.buf = {
            'title': None,
            'rows': [],
            'footers': []
        }

    def make_key(self, value):
        """ Make camelCase variant of value. """
        if value:
            parts = [self.key_filter.sub('', x)
                     for x in self.key_split.split(value.lower())]
            key = parts[0] + ''.join(map(str.capitalize, parts[1:]))
        else:
            key = ''
        if key in self.seen_keys:
            i = 1
            while '%s%d' % (key, i) in self.seen_keys:
                i += 1
            key = '%s%d' % (key, i)
        self.seen_keys.add(key)
        return key

    def cell_format(self, value):
        return rendering.vtmlrender(value).text()

    def print_header(self):
        self.buf['title'] = self.title
        self.keys[:] = map(self.make_key, self.headers)

    def print_rendered(self, rendered_values):
        self.buf['rows'].extend(dict(zip(self.keys, x))
                                for x in rendered_values)

    def close(self, exception=None):
        if exception and any(exception):
            return
        print(json.dumps(self.buf, indent=4, sort_keys=True), file=self.file)

Table.register_renderer(JSONTableRenderer)


class CSVTableRenderer(TableRenderer):
    """ Generate CSV (comma delimited) output of the table. """

    name = 'csv'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.writer = csv.writer(self.file)

    def cell_format(self, value):
        return rendering.vtmlrender(value).text()

    def print_footer(self, content):
        """ CSV does not support footers. """
        pass

    def print_header(self):
        self.writer.writerow(self.headers)

    def print_rendered(self, rendered_values):
        self.writer.writerows(rendered_values)

Table.register_renderer(CSVTableRenderer)


class MarkdownTableRenderer(PlainTableRenderer):
    """ Render Markdown text format output of the table. """

    name = 'md'

    def capture_table_state(self, table):
        super().capture_table_state(table)
        # Reserve initial space based on headers and min MD reqs.
        self.width = sum(max(len(h) + c['padding'], 3)
                         for h, c in zip(self.headers, self.colspec))
        self.width += 2  # borders

    def mdprint(self, *columns):
        print('|%s|' % '|'.join(map(str, columns)), file=self.file)

    def print_header(self):
        if self.title:
            print("**%s**" % self.title, file=self.file)
        headers = [rendering.VTML(x or '') for x in self.headers]
        self.mdprint(*map(str, self.format_row(headers)))
        self.mdprint(*("-" * (width + colspec['padding'])
                     for width, colspec in zip(self.widths, self.colspec)))

    def print_footer(self, content):
        print("_%s_" % content, file=self.file)

    def print_rendered(self, rendered_values):
        for row in rendered_values:
            self.mdprint(*self.format_row(row))

Table.register_renderer(MarkdownTableRenderer)


def tabulate(data, header=True, headers=None, accessors=None,
             **table_options):
    """ Shortcut function to produce tabular output of data without the
    need to create and configure a Table instance directly. The function
    does however return a table instance when it's done for any further use
    by the user. """
    if header and not headers:
        data = iter(data)
        try:
            headers = next(data)
        except StopIteration:
            pass
    if headers and hasattr(headers, 'items') and accessors is None:
        # Dict mode; Build accessors and headers from keys of data.
        data = itertools.chain([headers], data)
        accessors = list(headers)
        headers = [' '.join(map(str.capitalize, x.replace('_', ' ').split()))
                   for x in accessors]
    t = Table(headers=headers, accessors=accessors, **table_options)
    try:
        t.print(data)
    except RowsNotFound:
        pass
    return t
