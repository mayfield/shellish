
import atexit
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


def ignore_broken_pipe():
    """ If a shellish program has redirected stdio it is subject to erroneous
    "ignored" exceptions during the interpretor shutdown. This essentially
    beats the interpretor to the punch by closing them early and ignoring any
    broken pipe exceptions. """
    for f in sys.stdin, sys.stdout, sys.stderr:
        try:
            f.close()
        except BrokenPipeError:
            pass

atexit.register(ignore_broken_pipe)


from .command import *
from .autocommand import *
