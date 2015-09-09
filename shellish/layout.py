"""
Functions for displaying content with screen aware layout.
"""

import collections
import html.parser
import math
import shutil
import sys

__public__ = ['columnize', 'Table', 'tabulate', 'vtprint', 'Tree', 'dicttree',
              'TreeNode']


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

vtparser = VTParser()


def vtprint(*unformatted, **options):
    """ Follow normal print() signature but look for vt100 codes for richer
    output. I've intentionally left ouf color for personal reasons. """
    formatted = []
    for obj in unformatted:
        try:
            vtparser.feed(str(obj))
            vtparser.close()
        except:
            formatted.append(obj)
        else:
            formatted.append(''.join(vtparser.buf))
        finally:
            vtparser.reset()
    print(*formatted, **options)


def columnize(items, width=None, file=sys.stdout, print=vtprint):
    """ Smart display width handling when showing a list of stuff. """
    if not items:
        return
    if width is None:
        width, h = shutil.get_terminal_size()
    items = tuple(str(x) for x in items)
    colsize = len(max(items, key=len)) + 2
    cols = width // colsize
    if cols < 2:
        for x in items:
            print(x, file=file)
        return
    fmt = '%%-%ds' % colsize
    lines = math.ceil(len(items) / cols)
    for i in range(lines):
        row = items[i:None:lines]
        print((fmt*len(row)) % row, file=file)


class Table(object):
    """ Capture the state for a table such as column sizes and headers. """

    header_format = '<reverse>%s</reverse>'
    pad = 2
    cliptext_format = '<dim>%s</dim>'
    cliptext = '\u2026'  # ... as single char
    try:
        cliptext.encode(sys.stdout.encoding)
    except UnicodeEncodeError:
        cliptext = '...'

    def __init__(self, column_spec=None, headers=None, width=None, clip=True,
                 flex=True, file=sys.stdout, print=vtprint,
                 header_format=None, cliptext_format=None, cliptext=None,
                 min_column_width=None, column_pad=None):
        """ The .column_spec should be a list of width specs; Whole numbers
        are char widths, fractions are percentages of available width and None
        indicates the column is unspecified.  Unspec(ified) columns are then
        calculated at render time according to the .flex setting.  Note that
        the length of the column_spec list decides the column count for the
        the table.  It is permissible to change the column_spec but it will
        cause the table to be rerendered on the next write.

            Eg. column_spec=[
                    25, # fixed width, 25 chars
                    50, # fixed width, 50 chars
                    0.33, # 33% percent of total available space
                    None, # if flex=True will size to row content
                    None  # if flex=False will split remainder
                ]

        The .headers arg should contain a list of strings to display on the
        first line or be unset to skip the header line.

        If .flex is turned on and you have unspec columns (None) the render
        method will scan your initial data stream to determine the best widths
        to use.  It is permissible to submit your entire data set at this
        point if you have enough memory.

        By default the columns will clip text that overflows; Set .clip to
        False to disable this behavior but be warned the table will not look
        good. """
        self._column_spec = column_spec
        self.headers = headers
        self.width = width
        self.clip = clip
        self.overflow = self.overflow_clip if clip else self.overflow_show
        self.flex = flex
        self.file = file
        self.print = print
        self.min_column_width = min_column_width
        if header_format is not None:
            self.header_format = header_format
        if cliptext_format is not None:
            self.cliptext_format = cliptext_format
        if cliptext is not None:
            self.cliptext = cliptext
        if column_pad is not None:
            self.pad = column_pad
        self.reset()

    @property
    def column_spec(self):
        return self._column_spec

    @column_spec.setter
    def column_spec(self, spec):
        self._column_spec = spec
        self.reset()

    def reset(self):
        """ Clear render state, so the table can be reused. """
        self.render_spec = {}

    def overflow_show(self, items, widths):
        return tuple(items)

    def overflow_clip(self, items, widths):
        clipseq = self.cliptext_format % self.cliptext
        cliplen = len(self.cliptext)
        return tuple('%s%s' % (str(item)[:width - cliplen], clipseq)
                     if len(str(item)) > width else item
                     for item, width in zip(items, widths))

    def render(self, seed_data):
        """ Consume and analyze everything we know up to this point and set
        render specifications.  This function will do flex calculations if we
        are configured for that, so any subsequent calls to .write will not
        adjust the render spec.  To start over use .reset. """
        if self.render_spec:
            raise RuntimeError("Table already rendered")
        usable_width = self.width or shutil.get_terminal_size()[0]
        usable_width -= self.pad * len(self.column_spec)
        self.render_spec['usable_width'] = usable_width
        if self.flex and not hasattr(seed_data, '__getitem__'):
            seed_data = list(seed_data)  # Convert iter to sequence
        widths = self.calc_widths(seed_data)
        self.render_spec['calculated_widths'] = widths
        fmt = ''.join(('%%-%ds' % i) + (' ' * self.pad) for i in widths)
        self.render_spec['row_format'] = fmt
        if self.headers:
            headfmt = self.header_format % fmt
            self.print(headfmt % self.overflow(self.headers, widths),
                       file=self.file)
        self.write(seed_data)

    def write(self, rows):
        """ Write the data to our output stream (stdout).  If the table is not
        rendered yet, we will force a render now. """
        if not self.render_spec:
            return self.render(rows)
        fmt = self.render_spec['row_format']
        widths = self.render_spec['calculated_widths']
        for x in rows:
            self.print(fmt % self.overflow(x, widths), file=self.file)

    def write_row(self, row):
        return self.write([row])

    def calc_widths(self, sample_data):
        """ Convert the column_spec into absolute col widths. """
        spec = list(self.column_spec)
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
                for i, width in self.calc_flex(sample_data, remaining, unspec):
                    spec[i] = width
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
            lengths = [len(str(x[i])) for x in data]
            if self.headers:
                lengths.append(len(self.headers[i]))
            counts = collections.Counter(lengths)
            colstats.append({
                "counts": counts,
                "offt": max(lengths),
                "chop_mass": 0,
                "chop_count": 0,
                "total_mass": sum(a * b for a, b in counts.items())
            })
        if self.clip:
            self.adjust_clipping(max_width, colstats)
        return zip(cols, (x['offt'] for x in colstats))

    def adjust_clipping(self, max_width, colstats):
        """ Clip the columns based on the least negative affect it will have
        on the viewing experience.  We take note of the total character mass
        that will be clipped when each column should be narrowed.  The actual
        score for clipping is based on percentage of total character mass,
        which is the total number of characters in the column. """
        next_score = lambda x: (x['counts'][x['offt']] + x['chop_mass'] + \
                                x['chop_count']) / x['total_mass']
        cur_width = lambda: sum(x['offt'] for x in colstats)
        min_width = self.min_column_width or len(self.cliptext)
        while cur_width() > max_width:
            nextaffects = [(next_score(x), i) for i, x in enumerate(colstats)
                           if x['offt'] > min_width]
            if not nextaffects:
                break  # All columns are as small as they can get.
            nextaffects.sort()
            chop = colstats[nextaffects[0][1]]
            if chop['offt'] < len(self.cliptext):
                raise SystemExit("NOPE, never again, right? %s" % chop)
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
