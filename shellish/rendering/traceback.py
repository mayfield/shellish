"""
VTML traceback/exception formatting and printing

Many of the methods take from the naming convention of the standard library's
traceback module.
"""

import traceback
from . import vtml


def format_exception(exc, indent=0, pad='  '):
    """ Take an exception object and return a generator with vtml formatted
    exception traceback lines. """
    from_msg = None
    if exc.__cause__ is not None:
        indent += yield from format_exception(exc.__cause__, indent)
        from_msg = traceback._cause_message.strip()
    elif exc.__context__ is not None and not exc.__suppress_context__:
        indent += yield from format_exception(exc.__context__, indent)
        from_msg = traceback._context_message.strip()
    padding = pad * indent
    if from_msg:
        yield '\n%s%s\n' % (padding, from_msg)
    yield '%s<b><u>Traceback (most recent call last)</u></b>' % padding
    tblist = traceback.extract_tb(exc.__traceback__)
    tbdepth = len(tblist)
    for x in tblist:
        depth = '%d.' % tbdepth
        yield '%s<dim>%-3s</dim> <cyan>File</cyan> "<blue>%s</blue>", ' \
              'line <u>%d</u>, in <b>%s</b>' % (padding, depth, x.filename,
              x.lineno, x.name)
        yield '%s      %s' % (padding, x.line)
        tbdepth -= 1
    yield '%s<b><red>%s</red>: %s</b>' % (padding, type(exc).__name__, exc)
    return indent + 1


def print_exception(*args, file=None, **kwargs):
    """ Print the formatted output of an exception object. """
    for line in format_exception(*args, **kwargs):
        vtml.vtmlprint(line, file=file)
