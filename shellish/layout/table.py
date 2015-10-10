"""
Table layout.
"""

import collections
import itertools
import math
import operator
import shutil
import sys
import time
from . import vtml


class Table(object):
    """ A visual layout for row oriented data (like csv).  Most of the code
    here is dedicated to fitting the data as losslessly as possible onto a
    terminal screen.  The basic design goal is to fit your rows onto the
    screen without overflowing;  However a table instance can be configured
    to overflow if desired (clip=False).  For detailed help on using this
    class, see the __init__ method, or use the helper function tabulate() for
    simple use cases. """

    column_padding = 2
    column_align = 'left'  # {left,right,center}
    title_align = 'left'
    cliptext = '\u2026'  # ... as single char
    clip_default = True
    try:
        cliptext.encode(sys.stdout.encoding)
    except UnicodeEncodeError:
        cliptext = '...'
    column_minwidth = len(cliptext)
    renderer_types = {}

    # You probably shouldn't mess with these unless you really need custom
    # rendering performance.  Chances are you really don't and should
    # manage your data stream more carefully first.
    min_render_prefill = 5
    max_render_prefill = 200
    max_render_delay = 2

    def __init__(self, columns=None, headers=None, accessors=None, width=None,
                 clip=None, flex=True, file=sys.stdout, cliptext=None,
                 column_minwidth=None, column_padding=None, column_align=None,
                 renderer=None, title=None, title_align=None):
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
        self.columns_def = columns
        self.accessors_def = accessors
        self.headers = headers
        self.width = width
        self.flex = flex
        self.file = file
        self.default_renderer = None
        clip_fallback = self.clip_default
        if not renderer:
            if file is not sys.stdout or not vtml.is_terminal():
                renderer = 'plain'
                if clip is None:
                    clip_fallback = False
            else:
                renderer = 'terminal'
        self.renderer_class = self.lookup_renderer(renderer)
        self.clip = clip if clip is not None else clip_fallback
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

    def lookup_renderer(self, name):
        return self.renderer_types[name]

    @classmethod
    def register_renderer(cls, renderer):
        cls.renderer_types[renderer.name] = renderer

    @classmethod
    def unregister_renderer(cls, renderer):
        del cls.renderer_types[renderer.name]

    def make_accessors(self, columns):
        if not self.accessors_def:
            accessors = [operator.itemgetter(i) for i in range(columns)]
        else:
            accessors = self.accessors_def[:]
            for i, x in enumerate(accessors):
                if not callable(x):
                    accessors[i] = operator.itemgetter(x)
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

    def make_renderer(self, data=None):
        """ Consume and analyze everything we know up to this point and create
        a renderer instance that can be used for writing rows hence forth. """
        columns = (self.columns_def and len(self.columns_def)) or \
                  (self.headers and len(self.headers)) or \
                  (self.accessors_def and len(self.accessors_def))
        if not columns:
            if data:
                # Peek into the data stream as a last resort.
                tmp_iter = iter(data)
                peek = next(tmp_iter)
                columns = len(peek)
                data = itertools.chain([peek], tmp_iter)
            else:
                raise ValueError("Indeterminate column count")
        accessors = self.make_accessors(columns)
        colspec = self.create_colspec(columns)
        renderer = self.renderer_class(colspec, accessors, self, data)
        return renderer

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
    linebreak = '\u2014'  # solid dash
    try:
        linebreak.encode(sys.stdout.encoding)
    except UnicodeEncodeError:
        linebreak = '-'

    def __init__(self, colspec=None, accessors=None, table=None,
                 seed=None):
        """ All calculated values required for rendering a table are kept
        here.  In theory a single Table instance can be used to render
        multiple and differing datasets in a concurrent system.  Admittedly
        this is over-engineered for a CLI suite and the result of a lazy
        Sunday. """
        self.colspec = colspec
        self.accessors = accessors
        self.capture_table_state(table)
        self.prerendered = None
        self.seed = None
        if seed:
            self.prerendered, self.seed = self.seed_collect(seed)
        self.widths = self.calc_widths(self.prerendered)
        self.formatters = self.make_formatters()
        self.headers_drawn = not self.headers
        self.footers_drawn = False

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
        return vtml.vtmlrender(value)

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
                  'min_render_prefill'):
            setattr(self, x, getattr(table, x))
        if not self.width:
            self.width = shutil.get_terminal_size()[0]
        self.headers = table.headers and table.headers[:]

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
        pad = self.colspec[0]['padding']
        fmt = self.make_formatter(self.width - pad, pad, self.title_align)
        return fmt(value)

    def print_rendered(self, rendered_values):
        """ Format and print the pre-rendered data. """
        if not self.headers_drawn:
            self.print_header()
            self.headers_drawn = True
        for row in rendered_values:
            print(*self.format_row(row), sep='', file=self.file)

    def print(self, data):
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
        `spread` size. The result is a non-random and uniform. """
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
        headers = [x or '' for x in self.headers]
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
        return vtml.vtmlrender(value, plain=True)

Table.register_renderer(PlainTableRenderer)


class TerminalTableRenderer(TableRenderer):
    """ Render a table designed to fit/fill a terminal.  This renderer produces
    the most human friendly output when on a terminal device. """

    name = 'terminal'
    title_format = '\n<b>%s</b>\n'
    header_format = '<reverse>%s</reverse>'
    footer_format = '<dim>%s</dim>'

    def print_header(self):
        headers = [vtml.VTML(x or '') for x in self.headers]
        header = ''.join(map(str, self.format_row(headers)))
        if self.title:
            title = self.format_fullwidth(vtml.VTML(self.title))
            vtml.vtmlprint(self.title_format % title, file=self.file)
        vtml.vtmlprint(self.header_format % header, file=self.file)

    def print_footer(self, content):
        row = self.format_fullwidth(vtml.VTML(content))
        if not self.footers_drawn:
            self.footers_drawn = True
            print(self.linebreak * len(row), file=self.file)
        vtml.vtmlprint(self.footer_format % row, file=self.file)

Table.register_renderer(TerminalTableRenderer)


def tabulate(data, header=True, accessors=None, **table_options):
    """ Shortcut function to produce tabular output of data without the
    need to create and configure a Table instance directly. The function
    does however return a table instance when it's done for any further use
    by he user. """
    empty = not data
    headers = None
    if not empty and header:
        data = iter(data)
        try:
            headers = next(data)
        except StopIteration:
            empty = True
        else:
            if hasattr(headers, 'items') and accessors is None:
                # dict mode
                data = itertools.chain([headers], data)
                accessors = list(headers)
                headers = [x.capitalize().replace('_', ' ')
                           for x in accessors]
    t = Table(headers=headers, accessors=accessors, **table_options)
    if not empty:
        t.print(data)
    return t
