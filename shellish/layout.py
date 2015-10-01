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

__public__ = ['columnize', 'tabulate', 'vtmlprint', 'vtmlrender', 'dicttree']


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

    def text(self):
        """ Return just the text content of this string without opcodes. """
        return ''.join(x for x in self.values if not self.is_opcode(x))

    def is_opcode(self, item):
        return item and item[0] == '\033'

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
        if width <= self.visual_len:
            return self
        padlen = width - self.visual_len
        leftlen = padlen // 2
        rightlen = padlen - leftlen
        leftpad = (fillchar * leftlen,)
        rightpad = (fillchar * rightlen,)
        return type(self)(*leftpad+self.values+rightpad, length_hint=width)


def vtmlrender(vtmarkup):
    """ Look for vt100 markup and render to vt opcodes. """
    try:
        vtmlparser.feed(vtmarkup)
        vtmlparser.close()
    except:
        return VTML(str(vtmarkup))
    else:
        return vtmlparser.getvalue()
    finally:
        vtmlparser.reset()


def vtmlprint(*values, **options):
    """ Follow normal print() signature but look for vt100 codes for richer
    output. """
    print(*map(vtmlrender, values), **options)


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


class TableRenderer(object):
    """ A bundle of state for a particular table rendering job.  Each time a
    table is to be printed to a file or the screen a new instance of this
    object will be used to provide closure on the column spec and so forth.
    This is essentially frozen state computed from a table instance's
    definition. """

    def __init__(self, colspec=None, accessors=None, table=None,
                 seed_data=None):
        """ All calculated values required for rendering a table are kept
        here.  In theory a single Table instance can be used to render
        multiple and differing datasets in a concurrent system.  Admittedly
        this is over-engineered for a CLI suite and the result of a lazy
        Sunday. """
        self.colspec = colspec
        self.accessors = accessors
        self.capture_table_state(table)
        self.seed = seed_data and list(self.render_data(seed_data))
        self.widths = self.calc_widths(self.seed)
        self.formatters = self.create_formatters()
        self.headers_drawn = not self.headers

    def capture_table_state(self, table):
        """ Capture state from the table instance and store locally for safe
        keeping.  This is not specifically required but helps in keeping with
        our pseudo "frozen" nature. """
        for x in ('file', 'clip', 'cliptext', 'flex', 'width',
                  'header_format'):
            setattr(self, x, getattr(table, x))
        self.headers = table.headers and table.headers[:]

    def render_data(self, data):
        """ Get and format the data from the raw list of objects. """
        for obj in data:
            yield [vtmlrender(access(obj)) for access in self.accessors]

    def flush(self):
        """ Print any values stored in the render queue. """
        if self.seed:
            self.print_rendered(self.seed)
            self.seed = None

    def format_row(self, items):
        """ Apply overflow, justification and padding to a row. """
        return [formatter(x) for x, formatter in zip(items, self.formatters)]

    def print_rendered(self, rendered_values):
        """ Format and print the pre-rendered data. """
        if not self.headers_drawn:
            self.print_header()
        for row in rendered_values:
            print(*self.format_row(row), sep='', file=self.file)

    def print_header(self):
        headers = [VTML(x) for x in self.headers]
        header_row = ''.join(map(str, self.format_row(headers)))
        vtmlprint(self.header_format % header_row, file=self.file)
        self.headers_drawn = True

    def print(self, data):
        self.flush()
        self.print_rendered(self.render_data(data))

    def overflow_show(self, item, width):
        return item

    def overflow_clip(self, item, width):
        return item.clip(width, self.cliptext)

    def create_formatters(self):
        """ Create formatter functions for each column that factor the width
        and alignment settings.  They can then be stored in the render spec
        for faster justification processing. """
        align_funcs = {
            "left": 'ljust',
            "right": 'rjust',
            "center": 'center'
        }
        formatters = []
        overflow = self.overflow_clip if self.clip else self.overflow_show
        for spec, inner_w in zip(self.colspec, self.widths):
            align_fnname = align_funcs[spec['align']]
            outer_w = inner_w + spec['padding']
            align = operator.methodcaller(align_fnname, inner_w)
            def fn(x, inner_w=inner_w, outer_w=outer_w, align=align):
                return align(overflow(x, inner_w)).center(outer_w)
            formatters.append(fn)
        return formatters

    def calc_widths(self, sample_data):
        """ Convert the colspec into absolute col widths. """
        usable_width = self.width or shutil.get_terminal_size()[0]
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
                percol = math.floor(remaining / len(unspec))
                for i in unspec:
                    spec[i] = percol
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
            for x in colstats[:-1]:
                x['offt'] = math.floor((x['offt'] / required) * max_width)
                remaining -= x['offt']
            if colstats:
                colstats[-1]['offt'] = remaining
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


class Table(object):
    """ A visual layout for row oriented data (like csv).  Most of the code
    here is dedicated to fitting the data as losslessly as possible onto a
    terminal screen.  The basic design goal is to fit your rows onto the
    screen without overflowing;  However a table instance can be configured
    to overflow if desired (clip=False).  For detailed help on using this
    class, see the __init__ method, or use the helper function tabulate() for
    simple use cases. """

    header_format = '<reverse>%s</reverse>'
    column_padding = 2
    column_align = 'left'  # {left,right,center}
    cliptext = '\u2026'  # ... as single char
    try:
        cliptext.encode(sys.stdout.encoding)
    except UnicodeEncodeError:
        cliptext = '...'
    column_minwidth = len(cliptext)

    def __init__(self, columns=None, headers=None, accessors=None, width=None,
                 clip=True, flex=True, file=sys.stdout, header_format=None,
                 cliptext=None, column_minwidth=None, column_padding=None,
                 column_align=None):
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
        self.columns_def = columns
        self.accessors_def = accessors
        self.headers = headers
        self.width = width
        self.clip = clip
        self.flex = flex
        self.file = file
        self.default_renderer = None
        if header_format is not None:
            self.header_format = header_format
        if cliptext is not None:
            self.cliptext = cliptext
        if column_padding is not None:
            self.column_padding = column_padding
        if column_minwidth is not None:
            self.column_minwidth = column_minwidth
        if column_align is not None:
            self.column_align = column_align

    def create_accessors(self, columns):
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

    def render(self, seed_data=None):
        """ Consume and analyze everything we know up to this point and create
        a renderer instance that can be used for writing rows hence forth. """
        columns = (self.columns_def and len(self.columns_def)) or \
                  (self.headers and len(self.headers)) or \
                  (self.accessors_def and len(self.accessors_def))
        if not columns:
            if seed_data:
                # Peek into the data stream as a last resort.
                seediter = iter(seed_data)
                peek = next(seediter)
                columns = len(peek)
                seed_data = itertools.chain([peek], seediter)
            else:
                raise ValueError("Indeterminate column count")
        accessors = self.create_accessors(columns)
        colspec = self.create_colspec(columns)
        renderer = TableRenderer(colspec, accessors, self, seed_data)
        self.default_renderer = renderer
        return renderer

    def print(self, rows):
        """ Write the data to our output stream (stdout).  If the table is not
        rendered yet, we will force a render now. """
        if not self.default_renderer:
            r = self.render(rows)
            r.flush()
            return
        self.default_renderer.print(rows)

    def print_row(self, row):
        return self.print([row])


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

    def __init__(self, value, children=None):
        self.value = value
        self.children = children if children is not None else []

    def __lt__(self, item):
        return self.value < item.value


class Tree(object):
    """ Construct a visual tree from a data source. """

    tree_L = '└── '.encode().decode()
    tree_T = '├── '
    tree_vertspace = '│   '
    try:
        tree_L.encode(sys.stdout.encoding)
    except UnicodeEncodeError:
        tree_L = '\-- '
        tree_T = '+-- '
        tree_vertspace = '|   '

    def __init__(self, formatter=None, sort_key=None):
        self.formatter = formatter or (lambda x: x.value)
        self.sort_key = sort_key

    def render(self, nodes, prefix=None):
        end = len(nodes) - 1
        if self.sort_key is not False:
            nodes = sorted(nodes, key=self.sort_key)
        for i, x in enumerate(nodes):
            if prefix is not None:
                line = [prefix]
                if end == i:
                    line.append(self.tree_L)
                else:
                    line.append(self.tree_T)
            else:
                line = ['']
            vtmlprint(''.join(line) + self.formatter(x))
            if x.children:
                if prefix is not None:
                    line[-1] = '    ' if end == i else self.tree_vertspace
                self.render(x.children, prefix=''.join(line))


def dicttree(data, **options):
    """ Render a tree structure based on a well formed dictionary. The keys
    should be titles and the values are children of the node or None if it's
    a leaf node.  E.g.

        sample = {
            "Leaf 1": None,
            "Leaf 2": None,
            "Branch A": {
                "Sub Leaf 1": None,
                "Sub Branch": {
                    "Deep Leaf": None
                }
            },
            "Branch B": {
                "Sub Leaf 2": None
            }
        }
    """
    def crawl(dictdata):
        return [TreeNode(k, v and crawl(v)) for k, v in dictdata.items()]
    t = Tree(**options)
    t.render(crawl(data))
    return t
