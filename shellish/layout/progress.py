"""
Visual progress indicators.
"""

import math
import shutil
import sys
from . import vtml


class ProgressBar(object):
    """ Progress bar class for manual control. """

    partials = vtml.beststr('▏▎▎▍▍▌▌▋▋▊▊▉▉█', '#')
    fill = vtml.beststr('▯', '-')

    def __init__(self, min=0, max=1, width=None, file=None, prefix=' ',
                 suffix=' ', bar_style='', fill_style='', show_percent=True):
        if width is None:
            width = shutil.get_terminal_size()[0]
        if file is None:
            self.file = sys.stderr
        self.min_value = min
        self.max_value = max
        self.width = width
        self.bar_width = width - len(prefix) - len(suffix)
        if show_percent:
            self.bar_width -= 5
        self.prefix = prefix
        self.suffix = suffix
        self.bar_style = bar_style
        self.fill_style = fill_style
        self.show_percent = show_percent

    def draw(self):
        pct = (self.value - self.min_value) / self.max_value
        chars = pct * self.bar_width
        partial = chars % 1
        partial_idx = math.floor(partial * len(self.partials))
        wholechars = math.floor(chars)
        bar = (self.partials[-1] * wholechars)
        if len(bar) < self.bar_width:
            bar += self.partials[partial_idx]
        fill = self.fill * (self.bar_width - len(bar))
        if self.show_percent:
            pct = '%4.0f%%' % (pct * 100)
        vtml.vtmlprint('\r', self.prefix, self.bar_style + bar,
                       self.fill_style + fill, pct, self.suffix, sep='',
                       end='', file=self.file, flush=True)

    def set(self, value):
        self.value = value
        self.draw()

    def clear(self):
        vtml.vtmlprint('\r', ' ' * self.width, file=self.file)


def progressbar(stream, clear=False, prefix='Loading: ', width=0.5, **options):
    """ Generator filter to print a progress bar. """
    size = len(stream)
    if not size:
        return stream
    if 'width' not in options:
        if width < 1:
            width = round(shutil.get_terminal_size()[0] * width)
        options['width'] = width
    b = ProgressBar(max=size, prefix=prefix, **options)
    b.set(0)
    for i, x in enumerate(stream, 1):
        b.set(i)
        yield x
    if clear:
        b.clear()
    else:
        print()
