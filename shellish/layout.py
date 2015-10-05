"""
Functions for displaying content with screen aware layout.
"""

import collections
import functools
import html.parser
import itertools
import math
import operator
import shutil
import sys
import time

__public__ = ['columnize', 'tabulate', 'vtmlprint', 'vtmlrender', 'dicttree',
              'Table']


def is_terminal():
    """ Return true if the device is a terminal as apposed to a pipe or
    file.  This is usually used to determine if vt100 or unicode characters
    should be used or not. """
    fallback = object()
    return shutil.get_terminal_size((fallback, 0))[0] is not fallback


class VTMLParser(html.parser.HTMLParser):
    """ Add some SGML style tag support for a few VT100 operations. """

    tags = {
        'normal': '\033[0m',
        'b': '\033[1m',
        'dim': '\033[2m',
        'u': '\033[4m',
        'blink': '\033[5m',
        'reverse': '\033[7m'
    }

    def reset(self):
        self.state = [self.tags['normal']]
        self.buf = []
        self.open_tags = []
        super().reset()

    def handle_starttag(self, tag, attrs):
        opcode = self.tags[tag]
        self.state.append(opcode)
        self.open_tags.append(tag)
        self.buf.append(opcode)

    def handle_endtag(self, tag):
        if self.open_tags[-1] != tag:
            raise SyntaxError("Bad close tag: %s; Expected: %s" % (tag,
                              self.open_tags[-1]))
        del self.open_tags[-1]
        del self.state[-1]
        self.buf.extend(self.state)

    def handle_data(self, data):
        self.buf.append(data)

    def close(self):
        super().close()
        if self.open_tags:
            self.buf.append(self.state[0])

    def getvalue(self):
        return VTML(*self.buf)

vtmlparser = VTMLParser()


@functools.total_ordering
class VTML(object):
    """ A str-like object that has an adjusted length to compensate for
    nonvisual vt100 opcodes which do not occupy space in the output. """

    __slots__ = [
        'values',
        'visual_len'
    ]
    reset_opcode = '\033[0m'

    def __init__(self, *values, length_hint=None):
        self.values = values
        if length_hint is None:
            self.visual_len = sum(len(x) for x in values
                                  if not self.is_opcode(x))
        else:
            self.visual_len = length_hint

    def __len__(self):
        return self.visual_len

    def __str__(self):
        return ''.join(self.values)

    def __repr__(self):
        return repr(str(self))

    def __eq__(self, other):
        return str(self) == str(other)

    def __lt__(self, other):
        return str(self) < str(other)

    def __add__(self, item):
        return type(self)(*(self.values + item.values))

    def is_opcode(self, item):
        """ Is the string item a vt100 op code. Empty strings return True."""
        return item and item[0] == '\033'

    def text(self):
        """ Return just the text content of this string without opcodes. """
        return ''.join(x for x in self.values if not self.is_opcode(x))

    def plain(self):
        """ Similar to `text` but returns valid VTML instance. """
        return type(self)(*itertools.filterfalse(self.is_opcode, self.values))

    def clip(self, length, cliptext=''):
        """ Use instead of slicing to compensate for opcode behavior. """
        if length < 0:
            raise ValueError("Negative clip invalid")
        cliplen = len(cliptext)
        if length < cliplen:
            raise ValueError("Clip length too small: %d < %d" % (length,
                             cliplen))
        if length >= self.visual_len:
            return self
        remaining = length - cliplen
        buf = []
        last_opcode = ''
        for x in self.values:
            if not remaining:
                break
            elif self.is_opcode(x):
                buf.append(x)
                last_opcode = x
            else:
                fragment = x[:remaining]
                remaining -= len(fragment)
                buf.append(fragment)
        if cliptext:
            buf.append(cliptext)
        if last_opcode and last_opcode != self.reset_opcode:
            buf.append(self.reset_opcode)
        return type(self)(*buf, length_hint=length)

    def ljust(self, width, fillchar=' '):
        if width <= self.visual_len:
            return self
        pad = (fillchar * (width - self.visual_len),)
        return type(self)(*self.values+pad, length_hint=width)

    def rjust(self, width, fillchar=' '):
        if width <= self.visual_len:
            return self
        pad = (fillchar * (width - self.visual_len),)
        return type(self)(*pad+self.values, length_hint=width)

    def center(self, width, fillchar=' '):
        """ Center strings so uneven padding always favors trailing pad.  When
        centering clumps of text this produces better results than str.center
        which alternates which side uneven padding occurs on. """
        if width <= self.visual_len:
            return self
        padlen = width - self.visual_len
        leftlen = padlen // 2
        rightlen = padlen - leftlen
        leftpad = fillchar * leftlen
        rightpad = fillchar * rightlen
        chained = (leftpad,) + self.values + (rightpad,)
        return type(self)(*chained, length_hint=width)


def vtmlrender(vtmarkup, plain=None):
    """ Look for vt100 markup and render to vt opcodes. """
    if isinstance(vtmarkup, VTML):
        return vtmarkup.plain() if plain else vtmarkup
    try:
        vtmlparser.feed(vtmarkup)
        vtmlparser.close()
    except:
        return VTML(str(vtmarkup))
    else:
        value = vtmlparser.getvalue()
        return value.plain() if plain else value
    finally:
        vtmlparser.reset()


def vtmlprint(*values, plain=None, **options):
    """ Follow normal print() signature but look for vt100 codes for richer
    output. """
    print(*[vtmlrender(x, plain=plain) for x in values], **options)


def columnize(items, width=None, file=sys.stdout):
    """ Smart display width handling when showing a list of stuff. """
    if not items:
        return
    if width is None:
        width, h = shutil.get_terminal_size()
    items = [vtmlrender(x) for x in items]
    maxcol = max(items, key=len)
    colsize = len(maxcol) + 2
    cols = width // colsize
    if cols < 2:
        for x in items:
            print(x, file=file)
        return
    lines = math.ceil(len(items) / cols)
    for i in range(lines):
        row = items[i:None:lines]
        print(*[x.ljust(colsize) for x in row], sep='', file=file)


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
            if file is not sys.stdout or not is_terminal():
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


class TableRenderer(object):
    """ A bundle of state for a particular table rendering job.  Each time a
    table is to be printed to a file or the screen a new instance of this
    object will be used to provide closure on the column spec and so forth.
    This is essentially frozen state computed from a table instance's
    definition. """

    name = None

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
        return vtmlrender(value)

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
        next_score = lambda x: (x['counts'][x['offt']] + x['chop_mass'] + \
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
            print(self.format_fullwidth(self.title))
        print(header, file=self.file)
        print('-' * len(header), file=self.file)

    def cell_format(self, value):
        return vtmlrender(value, plain=True)

Table.register_renderer(PlainTableRenderer)


class TerminalTableRenderer(TableRenderer):
    """ Render a table designed to fit/fill a terminal.  This renderer produces
    the most human friendly output when on a terminal device. """

    name = 'terminal'
    header_format = '<reverse>%s</reverse>'

    def print_header(self):
        headers = [VTML(x or '') for x in self.headers]
        header = ''.join(map(str, self.format_row(headers)))
        if self.title:
            title = self.format_fullwidth(VTML(self.title))
            vtmlprint('<reverse><b>%s</b></reverse>' % title, file=self.file)
        vtmlprint(self.header_format % header, file=self.file)

Table.register_renderer(TerminalTableRenderer)


def tabulate(data, header=True, **table_options):
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
    t = Table(headers=headers, **table_options)
    if not empty:
        t.print(data)
    return t


class TreeNode(object):

    def __init__(self, value, children=None, label=None):
        self.value = value
        self.label = label
        self.children = children if children is not None else []

    def __lt__(self, item):
        return self.value < item.value


class Tree(object):
    """ Construct a visual tree from a data source. """

    tree_L = '└── '
    tree_T = '├── '
    tree_vertspace = '│   '
    try:
        tree_L.encode(sys.stdout.encoding)
    except UnicodeEncodeError:
        tree_L = '\-- '
        tree_T = '+-- '
        tree_vertspace = '|   '

    def __init__(self, formatter=None, sort_key=None, plain=None):
        self.formatter = formatter or self.default_formatter
        self.sort_key = sort_key
        if plain is None:
            plain = not is_terminal()
        self.plain = plain

    def default_formatter(self, node):
        if node.label is not None:
            return '%s: <b>%s</b>' % (node.value, node.label)
        else:
            return str(node.value)

    def render(self, nodes, prefix=None):
        node_list = list(nodes)
        end = len(node_list) - 1
        if self.sort_key is not False:
            node_list.sort(key=self.sort_key)
        for i, x in enumerate(node_list):
            if prefix is not None:
                line = [prefix]
                if end == i:
                    line.append(self.tree_L)
                else:
                    line.append(self.tree_T)
            else:
                line = ['']
            yield vtmlrender(''.join(line + [self.formatter(x)]),
                             plain=self.plain)
            if x.children:
                if prefix is not None:
                    line[-1] = '    ' if end == i else self.tree_vertspace
                yield from self.render(x.children, prefix=''.join(line))


def dicttree(data, render_only=False, **options):
    """ Render a tree structure based on a well formed dictionary. The keys
    should be titles and the values are children of the node or None if it's
    an empty leaf node;  Primitives are valid leaf node labels too.  E.g.

        sample = {
            "Leaf 1": None,
            "Leaf 2": "I have a label on me",
            "Branch A": {
                "Sub Leaf 1 with float label": 3.14,
                "Sub Branch": {
                    "Deep Leaf": None
                }
            },
            "Branch B": {
                "Sub Leaf 2": None
            }
        }
    """
    def crawl(obj):
        for key, value in obj.items():
            if hasattr(value, 'items'):
                yield TreeNode(key, children=crawl(value))
            elif value is not None:
                yield TreeNode(key, label=value)
            else:
                yield TreeNode(key)
    t = Tree(**options)
    render_gen = t.render(crawl(data))
    if render_only:
        return render_gen
    else:
        for x in render_gen:
            print(x)
