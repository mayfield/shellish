
import sys


def linebuffered_stdout():
    """ Always line buffer stdout so pipes and redirects are CLI friendly. """
    if sys.stdout.line_buffering:
        return sys.stdout
    orig = sys.stdout
    new = type(orig)(orig.buffer, encoding=orig.encoding, errors=orig.errors,
                     line_buffering=True)
    new.mode = orig.mode
    return new

sys.stdout = linebuffered_stdout()

from .command import *
from .autocommand import *
from .syscomplete import *
from .interactive import *
