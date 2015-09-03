"""
Functions for displaying content with screen aware layout.
"""

import collections
import math
import shutil
import sys
import textwrap

__public__ = ['columnize']

def columnize(items, displaywidth=None, file=sys.stdout):
    """ Smart display width handling when showing a list of stuff. """
    if displaywidth is None:
        displaywidth, h = shutil.get_terminal_size()
    items = tuple(str(x) for x in items)
    colsize = len(max(items, key=len)) + 2
    cols = displaywidth // colsize
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

    cliptext = '...'

    def __init__(self, colspecs, displaywidth=None, clip=False, flex=False,
                 file=sys.stdout):
        """ Colspecs is a list of (width, header) tuples.  If .flex is
        turned on and you have unspec columns the render method will scan your
        entire data source to determine the best widths to use. """
        self.widths_config = []
        self.headers = []
        for width_config, header in colspecs:
            self.widths_config.append(width_config)
            self.headers.append(header)
        self.displaywidth = displaywidth
        if not clip:
            self.overflow = self.overflow_show
        else:
            self.overflow = self.overflow_clip
        self.flex = flex
        self.file = file

    def overflow_show(self, items, widths):
        return tuple(items)

    def overflow_clip(self, items, widths):
        return tuple(textwrap.shorten(item, width-1, placeholder=self.cliptext)
                     for item, width in zip(items, widths))

    def render(self, data):
        tblwidth = self.displaywidth or shutil.get_terminal_size()[0]
        widths = self.calc_widths(data, tblwidth, self.widths_config)
        fmt = ''.join('%%-%ds' % i for i in widths)
        print(fmt % self.overflow(self.headers, widths), file=self.file)
        for x in data:
            print(fmt % self.overflow(x, widths), file=self.file)

    def calc_flex(self, data, max_width, cols):
        """ Scan the entire data source returning the best width for each
        column given the width constraint.  If some columns will clip we
        calculate the best concesion widths. """
        colstats = []
        min_width = len(self.cliptext)
        for i in cols:
            lengths = [len(x[i]) + min_width for x in data]
            colstats.append({
                "counts": collections.Counter(lengths),
                "offt": max(lengths)
            })
        cur_width = lambda: sum(x['offt'] for x in colstats)
        print(colstats)
        while cur_width() > max_width:
            nexteffect = [(x['counts'].get(x['offt'] - 1, 0)
                           if x['offt'] > min_width else 1e1000, i)
                          for i, x in enumerate(colstats)]
            nexteffect.sort()
            print("shortening:", nexteffect)
            colstats[nexteffect[0][1]]['offt'] -= 1
        print("holy shit we did it")
        return zip(cols, (x['offt'] for x in colstats))
        tot = sum(weights.values())
        for key, v in weights.items():
            weights[key] = v / tot
        return weights

    def calc_widths(self, data, tblwidth, widths=None):
        """ Convert the widths configs into absolute col widths. """
        if widths is None:
            widths = self.widths_config
        widths = widths[:]
        chars_rem = tblwidth
        unspec = []
        for i, x in enumerate(widths):
            if x is None:
                unspec.append(i)
            elif x > 0 and x < 1:
                widths[i] = w = math.floor(x * tblwidth)
                chars_rem -= w
            else:
                chars_rem -= x
        if unspec:
            if self.flex:
                for i, width in self.calc_flex(data, chars_rem, unspec):
                    widths[i] = width
            else:
                percol = math.floor(chars_rem / len(unspec))
                for i in unspec:
                    widths[i] = percol
        return widths
