"""
Display a list in columns.
"""

import math
import shutil
import sys
from .. import rendering


def columnize(items, width=None, file=sys.stdout):
    """ Smart display width handling when showing a list of stuff. """
    if not items:
        return
    if width is None:
        width = shutil.get_terminal_size()[0] if file is sys.stdout else 80
    items = [rendering.vtmlrender(x) for x in items]
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
