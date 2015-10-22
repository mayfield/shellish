"""
Translate HTML (simple) to VTML so it can be printed to a terminal or saved
to a text file in human readable format.
"""

import collections
import html
import html.parser
import re
import warnings
from . import vtml


class HTMLConv(html.parser.HTMLParser):
    """ Convert HTML to VTML. """

    strip = {
        "script",
        "style"
    }

    noop = {
        "head",
        "html",
        "div",
        "span"
    }

    whitespace = re.compile(r'\s+')

    def reset(self):
        self.buf = []
        self.tag_stack = []
        self.tag_attrs = collections.defaultdict(list)
        super().reset()

    def stripping(self):
        for x in self.strip:
            if x in self.tag_stack:
                return True
        return False

    def handle_starttag(self, tag, attrs):
        if tag in self.noop:
            return
        self.tag_stack.append(tag)
        if tag not in self.strip:
            handler = getattr(self, 'handle_start_%s' % tag, None)
            if handler:
                attrs = collections.OrderedDict(attrs)
                self.tag_attrs[tag].append(attrs)
                handler(tag, attrs)
            else:
                warnings.warn('unhandled tag: %s' % tag)

    def handle_endtag(self, tag):
        if tag in self.noop:
            return
        if self.tag_stack[-1] != tag:
            warnings.warn("Bad close tag: %s; Expected: %s" % (tag,
                          self.tag_stack[-1]))
            return
        del self.tag_stack[-1]
        if tag not in self.strip:
            handler = getattr(self, 'handle_end_%s' % tag, None)
            if handler:
                attrs = self.tag_attrs[tag].pop()
                handler(tag, attrs)

    def handle_data(self, data):
        if not self.stripping():
            self.buf.append(self.whitespace.sub(' ', data))

    def handle_start_b(self, tag, attrs):
        self.buf.append('<b>')

    def handle_end_b(self, tag, attrs):
        self.buf.append('</b>')

    def handle_start_u(self, tag, attrs):
        self.buf.append('<u>')

    def handle_end_u(self, tag, attrs):
        self.buf.append('</u>')

    def handle_start_h1(self, tag, attrs):
        self.buf.append('\n<b>')

    def handle_end_h1(self, tag, attrs):
        self.buf.append('</b>\n\n')

    handle_start_h2 = handle_start_h1
    handle_start_h3 = handle_start_h1
    handle_start_h4 = handle_start_h1
    handle_end_h2 = handle_end_h1
    handle_end_h3 = handle_end_h1
    handle_end_h4 = handle_end_h1

    def handle_start_a(self, tag, attrs):
        self.buf.append('<blue><u>')

    def handle_end_a(self, tag, attrs):
        href = attrs.get('href')
        if href:
            self.buf.append(' (%s)' % href)
        self.buf.append('</u></blue>')

    def handle_start_p(self, tag, attrs):
        self.buf.append('\n')

    def handle_end_p(self, tag, attrs):
        self.buf.append('\n')

    def handle_start_br(self, tag, attrs):
        self.buf.append('\n')

    def handle_end_br(self, tag, attrs):
        pass

    def handle_start_ol(self, tag, attrs):
        self.buf.append('\n')

    def handle_end_ol(self, tag, attrs):
        self.buf.append('\n')

    def handle_start_ul(self, tag, attrs):
        self.buf.append('\n')

    def handle_end_ul(self, tag, attrs):
        self.buf.append('\n')

    def handle_start_li(self, tag, attrs):
        for x in reversed(self.tag_stack):
            if x in ('ul', 'ol'):
                list_attrs = self.tag_attrs[x][-1]
                tag = x
                break
        else:
            warnings.warn("Bad LI tag is outside UL or OL")
        if tag == 'ol':
            bullet = '%d.' % list_attrs.setdefault('_index', 1)
            list_attrs['_index'] += 1
        else:
            bullet = vtml.beststr('●', '*')
        self.buf.append('<b> %s  </b>' % bullet)

    def handle_end_li(self, tag, attrs):
        self.buf.append('\n')

    def getvalue(self):
        return ''.join(self.buf)

htmlconv = HTMLConv()


def html2vtml(vtmarkup):
    """ Convert hypertext markup into vt markup.
    The output can be given to `vtmlrender` for converstion to VT100
    sequences. """
    try:
        htmlconv.feed(vtmarkup)
        htmlconv.close()
        return htmlconv.getvalue()
    finally:
        htmlconv.reset()


def htmlrender(htmarkup, **kwargs):
    """ Process HTML into printable VTML. """
    return vtml.vtmlrender(html2vtml(htmarkup), **kwargs)


def htmlprint(*values, plain=None, **options):
    """ Convert HTML to VTML and then print it.
    Follows same semantics as vtmlprint. """
    print(*[htmlrender(x, plain=plain) for x in values], **options)
