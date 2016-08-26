"""
Translate Markdown to VTML (via HTML) so it can be printed to a terminal or
saved to a text file in human readable format.
"""

import markdown2
from . import html

_md = markdown2.Markdown(extras=['fenced-code-blocks'])

def mdconvert(markdown):
    html = _md.convert(markdown)
    return html[:-1]


def mdrender(markdown, **kwargs):
    """ Process HTML into printable VTML. """
    return html.htmlrender(mdconvert(markdown), **kwargs)


def mdprint(*values, plain=None, **options):
    """ Convert HTML to VTML and then print it.
    Follows same semantics as vtmlprint. """
    print(*[mdrender(x, plain=plain) for x in values], **options)
