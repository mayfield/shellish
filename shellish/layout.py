"""
Functions for displaying content with screen aware layout.
"""

import collections
import functools
import html.parser
import math
import operator
import shutil
import sys

__public__ = ['columnize', 'tabulate', 'vtprint', 'dicttree']


class VTParser(html.parser.HTMLParser):
    """ Add some SGML style tag support for a few VT100 operations. """

    tags = {
        'normal': '\033[0m',
        'b': '\033[1m',
        'dim': '\033[2m',
        'ul': '\033[4m',
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
        return VTStr(self.buf)

vtparser = VTParser()


@functools.total_ordering
class VTStr(object):
    """ A str-like object that has a visual_length attr to compensate for
    vt100 opcodes that do not actual occupy space in the output on a term. """

    reset_opcode = '\033[0m'

    def __init__(self, values):
        self.values = values[:]
        self.visual_length = sum(len(x) for x in self.values
                                 if not self.is_opcode(x))

    def __str__(self):
        return ''.join(self.values)

    def __repr__(self):
        return repr(str(self))

    def __eq__(self, other):
        return str(self) == str(other)

    def __lt__(self, other):
        return str(self) < str(other)

    def __add__(self, item):
        # XXX Possibly support str(item).
        return type(self)(self.values + item.values)

    def text(self):
        """ Return just the text content of this string without opcodes. """
        return ''.join(x for x in self.values if not self.is_opcode(x))

    def is_opcode(self, item):
        return item.startswith('\033')

    def clip(self, length, cliptext=''):
        """ Use instead of slicing to compensate for opcode behavior. """
        if length < 0:
            raise ValueError("Negative clip invalid")
        cliplen = len(cliptext)
        if length < cliplen:
            raise ValueError("Clip size is too small for clip text")
        if length >= self.visual_length:
            return self
        length -= cliplen
        buf = []
        last_opcode = ''
        for x in self.values:
            if not length:
                break
            elif self.is_opcode(x):
                buf.append(x)
                last_opcode = x
            else:
                fragment = x[:length]
                length -= len(fragment)
                buf.append(fragment)
        if last_opcode and last_opcode != self.reset_opcode:
            buf.append(self.reset_opcode)
        if cliptext:
            buf.append(cliptext)
        return type(self)(buf)

    def padding(self, width, fillchar):
        pad = width - self.visual_length
        return fillchar * pad

    def ljust(self, width, fillchar=' '):
        return str(self) + self.padding(width, fillchar)

    def rjust(self, width, fillchar=' '):
        return self.padding(width, fillchar) + str(self)

    def center(self, width, fillchar=' '):
        pad = self.padding(width, fillchar)
        half = round(len(pad) / 2)
        left = pad[:half]
        right = pad[half:]
        return left + str(self) + right


def vtformat(unformatted, **options):
    """ Look for vt100 codes for richer output. """
    try:
        vtparser.feed(str(unformatted))
        vtparser.close()
    except:
        return VTStr([unformatted], 0)
    else:
        return vtparser.getvalue()
    finally:
        vtparser.reset()


def vtprint(*unformatted, **options):
    """ Follow normal print() signature but look for vt100 codes for richer
    output. """
    print(*[vtformat(x) for x in unformatted], **options)


def columnize(items, width=None, file=sys.stdout):
    """ Smart display width handling when showing a list of stuff. """
    if not items:
        return
    if width is None:
        width, h = shutil.get_terminal_size()
    items = [vtformat(x) for x in items]
    maxcol = max(items, key=operator.attrgetter('visual_length'))
    colsize = maxcol.visual_length + 2
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
    """ Capture the state for a table such as column sizes and headers. """

    header_format = '<reverse>%s</reverse>'
    column_padding = 2
    column_align = 'left'  # {left,right,center}
    column_minwidth = 0
    cliptext = '\u2026'  # ... as single char
    try:
        cliptext.encode(sys.stdout.encoding)
    except UnicodeEncodeError:
        cliptext = '...'

    def __init__(self, column_spec=None, headers=None, accessors=None,
                 width=None, clip=True, flex=True, file=sys.stdout,
                 header_format=None, cliptext=None, column_minwidth=None,
                 column_padding=None, column_align=None):
        """ The .column_spec should be a list of width specs or a style dict.
        Width specs can be whole numbers representing fixed char widths,
        fractions representing percentages of available table width or None
        if the column is unspec'd.  Unspec'd columns are then calculated at
        render time according to the .flex setting.  If not provided then all
        columns will be unspec'd.  E.g.

            >>> t = Table(column_spec=[
                25, # fixed width, 25 chars
                50, # fixed width, 50 chars
                0.33, # 33% percent of total available space
                None, # if flex=True will size to row content
                None  # if flex=False will split remainder
            ])

        The column_spec style dict supports the following properties:

            "width":    Follows the aforementioned column width definition.
            "minwidth": Minimum characters a column can be shrunken to.
            "padding":  Property for custom padding of individual columns.
                        Whole number of white space characters to add.
            "align":    How to justify the contents of the column. Valid
                        choices are 'left', 'right', and 'center'.

            E.g.

            >>> t = Table(column_spec=[{
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

        When any values are omitted from the column spec they will pickup
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
            >>> t.write_row({"three": "333", "one": "1", "two": "22"})

        If .flex is turned on and you have unspec columns (None) the render
        method will scan your initial data stream to determine the best widths
        to use.  It is permissible to submit your entire data set at this
        point if you have enough memory.

        By default the columns will clip text that overflows; Set .clip to
        False to disable this behavior but be warned the table will not look
        good. """
        colcount = (column_spec and len(column_spec)) or \
                   (accessors and len(accessors)) or \
                   (headers and len(headers))
        if not colcount:
            raise ValueError('Indeterminate column definition')
        if not accessors:
            accessors = [operator.itemgetter(i) for i in range(colcount)]
        else:
            for i, x in enumerate(accessors):
                if not callable(x):
                    accessors[i] = operator.itemgetter(x)
        if headers and len(headers) != colcount:
            raise ValueError('Incongruent headers count %d, expected %d' % (
                             len(headers), colcount))
        self.column_count = colcount
        self.headers = headers
        self.accessors = accessors
        self.width = width
        self.clip = clip
        self.overflow = self.overflow_clip if clip else self.overflow_show
        self.flex = flex
        self.file = file
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
        self.column_spec = self.calc_column_spec(column_spec)
        self.reset()

    def calc_column_spec(self, overrides_spec):
        """ Produce a full format column_spec dictionary.  The overrides spec
        can be a partial column_spec as described in the __init__ method's
        depiction of the .column_spec attribute. """
        spec = [{
            "width": None,
            "minwidth": self.column_minwidth,
            "padding": self.column_padding,
            "align": self.column_align
        } for x in range(self.column_count)]
        if overrides_spec:
            for dst, src in zip(spec, overrides_spec):
                if hasattr(src, 'items'):
                    dst.update(src)
                else:
                    dst['width'] = src
        return spec

    def reset(self):
        """ Clear render state, so the table can be reused. """
        self.render_spec = {}

    def overflow_show(self, item, width):
        return item

    def overflow_clip(self, item, width):
        return item.clip(width, self.cliptext)

    def format_row(self, items):
        """ Apply overflow, justification and padding to a row. """
        formatters = self.render_spec['formatters']
        return [formatter(x) for x, formatter in zip(items, formatters)]

    def render_data(self, data):
        """ Get and format the data from the raw list of objects. """
        for obj in data:
            yield [vtformat(access(obj)) for access in self.accessors]

    def render(self, seed_data):
        """ Consume and analyze everything we know up to this point and set
        render specifications.  This function will do flex calculations if we
        are configured for that, so any subsequent calls to .write will not
        adjust the render spec.  To start over use .reset. """
        if self.render_spec:
            raise RuntimeError("Table already rendered")
        rendered_data = list(self.render_data(seed_data))
        usable_width = self.width or shutil.get_terminal_size()[0]
        usable_width -= sum(x['padding'] for x in self.column_spec)
        self.render_spec['usable_width'] = usable_width
        self.render_spec['widths'] = w = self.calc_widths(rendered_data)
        self.render_spec['formatters'] = self.create_formatters(w)
        if self.headers:
            headers = [vtformat(x) for x in self.headers]
            header_row = ''.join(self.format_row(headers))
            vtprint(self.header_format % header_row, file=self.file)
        self.print_data(rendered_data)

    def print_data(self, data):
        """ Format and print the prerendered data. """
        for row in data:
            print(*self.format_row(row), sep='', file=self.file)

    def write(self, rows):
        """ Write the data to our output stream (stdout).  If the table is not
        rendered yet, we will force a render now. """
        if not self.render_spec:
            return self.render(rows)
        self.print_data(self.render_data(rows))

    def write_row(self, row):
        return self.write([row])

    def create_formatters(self, widths):
        """ Create formatter functions for each column that factor the width
        and alignment settings.  They can then be stored in the render spec
        for faster justification processing. """
        widths = self.render_spec['widths']
        align_funcs = {
            "left": 'ljust',
            "right": 'rjust',
            "center": 'center'
        }
        formatters = []
        for spec, width in zip(self.column_spec, widths):
            align_fnname = align_funcs[spec['align']]
            align_width = width + spec['padding']
            def closure(w):
                align = operator.methodcaller(align_fnname, align_width)
                return lambda x: align(self.overflow(x, w))
            formatters.append(closure(width))
        return formatters

    def calc_widths(self, sample_data):
        """ Convert the column_spec into absolute col widths. """
        spec = [x['width'] for x in self.column_spec]
        remaining = usable = self.render_spec['usable_width']
        unspec = []
        for i, x in enumerate(spec):
            if x is None:
                unspec.append(i)
            elif x > 0 and x < 1:
                spec[i] = w = math.floor(x * usable)
                remaining -= w
            else:
                remaining -= x
        if unspec:
            if self.flex:
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
            lengths = [x[i].visual_length for x in data]
            if self.headers:
                lengths.append(len(self.headers[i]))
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
        min_width = lambda x: self.column_spec[x['column']]['minwidth']
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


def tabulate(data, header=True, **table_options):
    """ Shortcut function to produce tabular output of data without the
    need to create and configure a Table instance directly. The function
    does however return a table instance when it's done for any further use
    by he user. """
    # Attempt to preserve sequence types as they require one less O(n) pass
    # over the data for Table.calc_flex().
    try:
        firstrow = data[0]
    except IndexError:
        firstrow = None
    except TypeError:
        try:
            firstrow = next(data)
        except StopIteration:
            firstrow = None
        if firstrow and not header:
            def it(first, remain):
                yield first
                for x in remain:
                    yield x
            data = it(firstrow, data)
    else:
        if header:
            data = data[1:]
    headers = firstrow if header else None
    colspec = [None] * len(firstrow) if firstrow else []
    t = Table(column_spec=colspec, headers=headers, **table_options)
    if firstrow and data:
        t.write(data)
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
            vtprint(''.join(line) + self.formatter(x))
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
