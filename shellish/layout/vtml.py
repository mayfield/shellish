"""
Functions for displaying content with screen aware layout.
"""

import functools
import html.parser
import itertools
import shutil


def is_terminal():
    """ Return true if the device is a terminal as apposed to a pipe or
    file.  This is usually used to determine if vt100 or unicode characters
    should be used or not. """
    fallback = object()
    return shutil.get_terminal_size((fallback, 0))[0] is not fallback


class VTMLParser(html.parser.HTMLParser):
    """ Add some SGML style tag support for a few VT100 operations. """

    tags = {
        'normal': 0,
        'b': 1,
        'dim': 2,
        'u': 4,
        'blink': 5,
        'reverse': 7,
        'black': 30,
        'red': 31,
        'green': 32,
        'yellow': 33,
        'blue': 34,
        'magenta': 35,
        'cyan': 36,
        'white': 37,
        'bgblack': 40,
        'bgred': 41,
        'bggreen': 42,
        'bgyellow': 43,
        'bgblue': 44,
        'bgmagenta': 45,
        'bgcyan': 46,
        'bgwhite': 47
    }

    def make_attr(self, *states):
        """ Generate a vt100 escape sequence for one or more states. """
        attrs = ';'.join(map(str, states))
        return '\033[%sm' % attrs

    def reset(self):
        self.state = []
        self.buf = []
        self.open_tags = []
        self.prestate = []
        super().reset()

    def handle_starttag(self, tag, attrs):
        opcode = self.tags[tag]
        self.state.append(opcode)
        self.prestate.append(opcode)
        self.open_tags.append(tag)

    def handle_endtag(self, tag):
        if self.open_tags[-1] != tag:
            raise SyntaxError("Bad close tag: %s; Expected: %s" % (tag,
                              self.open_tags[-1]))
        del self.open_tags[-1]
        del self.state[-1]
        if self.prestate:
            del self.prestate[-1]
        self.prestate.append(self.tags['normal'])
        self.prestate.extend(self.state)

    def handle_data(self, data):
        if self.prestate:
            # Flush prestate into a single esc-attr.
            self.buf.append(self.make_attr(*self.prestate))
            del self.prestate[:]
        self.buf.append(data)

    def close(self):
        super().close()
        if self.open_tags:
            self.buf.append(self.make_attr(self.tags['normal']))

    def getvalue(self):
        return VTML(*self.buf)

vtmlparser = VTMLParser()


@functools.total_ordering
class VTML(object):
    """ A str-like object that has an adjusted length to compensate for
    nonvisual vt100 opcodes which do not occupy space in the output. """

    __slots__ = [
        'values',
        'visual_len'
    ]
    reset_opcode = '\033[0m'

    def __init__(self, *values, length_hint=None):
        self.values = values
        if length_hint is None:
            self.visual_len = sum(len(x) for x in values
                                  if not self.is_opcode(x))
        else:
            self.visual_len = length_hint

    def __len__(self):
        return self.visual_len

    def __str__(self):
        return ''.join(self.values)

    def __repr__(self):
        return repr(str(self))

    def __eq__(self, other):
        return str(self) == str(other)

    def __lt__(self, other):
        return str(self) < str(other)

    def __add__(self, item):
        if not isinstance(item, (VTML, str)):
            raise TypeError("Invalid concatenation type: %s" % type(item))
        values = item.values if isinstance(item, VTML) else (item,)
        return type(self)(*(self.values + values))

    def is_opcode(self, item):
        """ Is the string item a vt100 op code. Empty strings return True."""
        return item and item[0] == '\033'

    def text(self):
        """ Return just the text content of this string without opcodes. """
        return ''.join(x for x in self.values if not self.is_opcode(x))

    def plain(self):
        """ Similar to `text` but returns valid VTML instance. """
        return type(self)(*itertools.filterfalse(self.is_opcode, self.values))

    def clip(self, length, cliptext=''):
        """ Use instead of slicing to compensate for opcode behavior. """
        if length < 0:
            raise ValueError("Negative clip invalid")
        cliplen = len(cliptext)
        if length < cliplen:
            raise ValueError("Clip length too small: %d < %d" % (length,
                             cliplen))
        if length >= self.visual_len:
            return self
        remaining = length - cliplen
        buf = []
        last_opcode = ''
        for x in self.values:
            if not remaining:
                break
            elif self.is_opcode(x):
                buf.append(x)
                last_opcode = x
            else:
                fragment = x[:remaining]
                remaining -= len(fragment)
                buf.append(fragment)
        if cliptext:
            buf.append(cliptext)
        if last_opcode and last_opcode != self.reset_opcode:
            buf.append(self.reset_opcode)
        return type(self)(*buf, length_hint=length)

    def ljust(self, width, fillchar=' '):
        if width <= self.visual_len:
            return self
        pad = (fillchar * (width - self.visual_len),)
        return type(self)(*self.values+pad, length_hint=width)

    def rjust(self, width, fillchar=' '):
        if width <= self.visual_len:
            return self
        pad = (fillchar * (width - self.visual_len),)
        return type(self)(*pad+self.values, length_hint=width)

    def center(self, width, fillchar=' '):
        """ Center strings so uneven padding always favors trailing pad.  When
        centering clumps of text this produces better results than str.center
        which alternates which side uneven padding occurs on. """
        if width <= self.visual_len:
            return self
        padlen = width - self.visual_len
        leftlen = padlen // 2
        rightlen = padlen - leftlen
        leftpad = fillchar * leftlen
        rightpad = fillchar * rightlen
        chained = (leftpad,) + self.values + (rightpad,)
        return type(self)(*chained, length_hint=width)


def vtmlrender(vtmarkup, plain=None):
    """ Look for vt100 markup and render to vt opcodes. """
    if isinstance(vtmarkup, VTML):
        return vtmarkup.plain() if plain else vtmarkup
    try:
        vtmlparser.feed(vtmarkup)
        vtmlparser.close()
    except:
        return VTML(str(vtmarkup))
    else:
        value = vtmlparser.getvalue()
        return value.plain() if plain else value
    finally:
        vtmlparser.reset()


def vtmlprint(*values, plain=None, **options):
    """ Follow normal print() signature but look for vt100 codes for richer
    output. """
    print(*[vtmlrender(x, plain=plain) for x in values], **options)
