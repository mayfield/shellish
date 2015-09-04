"""
Functions for displaying content with screen aware layout.
"""

import collections
import html.parser
import io
import math
import shutil
import sys

__public__ = ['columnize', 'Table', 'tabular', 'vt100_print']


class VT100Parser(html.parser.HTMLParser):
    """ Add some SGML style tag support for a few vt100 operations. """

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
        self.buf.append(self.state[0])

vt100parser = VT100Parser()


def vt100_print(*values, file=sys.stdout, **options):
    """ Follow normal print() signature but look for vt100 codes for richer
    output. I've intentionally left ouf color for now for strictly personal
    reasons. """
    prerender = io.StringIO()
    end_save = options.pop('end', None)
    print(*values, file=prerender, end='', **options)
    try:
        vt100parser.feed(prerender.getvalue())
        vt100parser.close()
        fullrender = ''.join(vt100parser.buf)
    finally:
        vt100parser.reset()
    print(fullrender, file=file, end=end_save, **options)


def columnize(items, width=None, file=sys.stdout, print=vt100_print):
    """ Smart display width handling when showing a list of stuff. """
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
                 flex=True, file=sys.stdout, print=vt100_print,
                 header_format=None, cliptext_format=None, cliptext=None,
                 min_column_width=None):
        """ The .column_spec should be a list of width specs; Whole numbers
        are char widths, fractions are percentages of available width and None
        indicates the column is unspecified.  Unspec(ified) columns are then
        calculated at render time according to the .flex setting.  Note that
        the length of the column_spec list decides the column count for the
        life of the table.

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
        self.headers = headers
        self.column_spec = column_spec
        self.column_count = len(column_spec)
        self.width = width
        if not clip:
            self.overflow = self.overflow_show
        else:
            self.overflow = self.overflow_clip
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
        self.reset()

    def reset(self):
        """ Clear render state, so the table can be reused. """
        self.render_spec = {}

    def overflow_show(self, items, widths):
        return tuple(items)

    def overflow_clip(self, items, widths):
        clipseq = self.cliptext_format % self.cliptext
        cliplen = len(self.cliptext)
        return tuple('%s%s' % (item[:width - cliplen], clipseq)
                     if len(item) > width else item
                     for item, width in zip(items, widths))

    def render(self, seed_data):
        """ Consume and analyze everything we know up to this point and set
        render specifications.  This function will do flex calculations if we
        are configured for that, so any subsequent calls to .write will not
        adjust the render spec.  To start over use .reset. """
        if self.render_spec:
            raise RuntimeError("Table already rendered")
        usable_width = self.width or shutil.get_terminal_size()[0]
        usable_width -= self.pad * self.column_count
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
        spec = self.column_spec[:]
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
            lengths = [len(x[i]) for x in data]
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
        cur_width = lambda: sum(x['offt'] for x in colstats)
        print(colstats)
        # The total character mass we WOULD be clipping for a column.
        # This is the rank for our clip algo.  We try to equalize the clip
        # mass for each column.
        next_mass = lambda x: x['counts'][x['offt']] + x['chop_mass'] + \
                              x['chop_count']
        min_width = self.min_column_width or len(self.cliptext)
        while cur_width() > max_width:
            nextaffects = [(next_mass(x) / x['total_mass'], i) for i, x in enumerate(colstats)
                           if x['offt'] > min_width]
            if not nextaffects:
                print("PREMATURE SMALL")
                print("PREMATURE SMALL")
                print("PREMATURE SMALL")
                break  # all columns are as small as they can get.
            nextaffects.sort()
            print("nexteffects", nextaffects)
            chop = colstats[nextaffects[0][1]]
            if chop['offt'] < len(self.cliptext):
                print("SHOULD SKIP!!!!!!", chop)
            chop['chop_count'] += chop['counts'][chop['offt']]
            chop['chop_mass'] += chop['chop_count']
            chop['offt'] -= 1
            print('chop', chop)
        return zip(cols, (x['offt'] for x in colstats))


def tabular(data, header=True, **table_options):
    """ Shortcut function to produce tabular output of data without the
    need to create and configure a Table instance directly. The function
    does however return a table instance when it's done for any further use
    by he user. """
    # Attempt to preserve sequence types as they require one less O(n) pass
    # over the data for Table.calc_flex().
    try:
        firstrow = data[0]
    except TypeError:
        firstrow = next(data)
        if not header:
            def it(first, remain):
                yield first
                for x in remain:
                    yield x
            data = it(firstrow, data)
    else:
        if header:
            data = data[1:]
    headers = firstrow if header else None
    colspec = [None] * len(firstrow)
    t = Table(column_spec=colspec, headers=headers, **table_options)
    t.write(data)
    return t
