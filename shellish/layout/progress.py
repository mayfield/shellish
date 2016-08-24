"""
Visual progress indicators.
"""

import math
import shutil
import sys
from .. import rendering


class ProgressBar(object):
    """ Progress bar class for more advanced control apps.  Most likely this
    should just be used by subclasses or by the generator functions. """

    partials = rendering.beststr('▏▎▎▍▍▌▌▋▋▊▊▉▉█', '#')
    fill = rendering.beststr('▯', '-')

    def __init__(self, min=0, max=1, width=None, file=None, prefix=' ',
                 suffix=' ', bar_style='', fill_style='', show_percent=True,
                 clear=False):
        if width is None:
            width = shutil.get_terminal_size()[0]
        if file is None:
            self.file = sys.stderr
        self.clear_on_exit = clear
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

    def __enter__(self):
        self.hide_cursor()
        return self

    def __exit__(self, *exc):
        if self.clear_on_exit:
            self.clear()
        else:
            print(file=self.file)
        self.restore_cursor()

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
        rendering.vtmlprint('\r', self.prefix, self.bar_style + bar,
                            self.fill_style + fill, pct, self.suffix, sep='',
                            end='', file=self.file, flush=True)

    def set(self, value):
        self.value = value
        self.draw()

    def clear(self):
        rendering.vtmlprint('\r', ' ' * self.width, file=self.file)

    def hide_cursor(self):
        print('\033[?25l', file=self.file)

    def restore_cursor(self):
        print('\033[?25h', file=self.file)


def progressbar(stream, prefix='Loading: ', width=0.5, **options):
    """ Generator filter to print a progress bar. """
    size = len(stream)
    if not size:
        return stream
    if 'width' not in options:
        if width <= 1:
            width = round(shutil.get_terminal_size()[0] * width)
        options['width'] = width
    with ProgressBar(max=size, prefix=prefix, **options) as b:
        b.set(0)
        for i, x in enumerate(stream, 1):
            yield x
            b.set(i)
