"""
Functions for displaying content with screen aware layout.
"""

import enum
import functools
import html.parser
import re
import sys

TAGS = {
    'b': 1,
    'dim': 2,
    'i': 3,
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
    'bgwhite': 47,
}


def beststr(*strings):
    """ Test if the output device can handle the desired strings. The options
    should be sorted by preference. Eg. beststr(unicode, ascii). """
    for x in strings:
        try:
            x.encode(sys.stdout.encoding)
        except UnicodeEncodeError:
            pass
        else:
            return x
    raise ValueError('No valid strings found')

# Regex for handling line wrapping...
#  * Splits by spaces, newlines and hypens.
#  * Hypens are kept on leftmost word.
#  * Newlines are not grouped with other whitespace.
#  * Other whitespace is grouped.
_textwrap_word_break = re.compile('(\n|[ \t\f\v\r]+|[^\s]+?-+)')
_whitespace = re.compile('[ \t\f\v\r]+')


def is_whitespace(value):
    return not not _whitespace.match(value)


def _add_slice(seq, slc):
    """ Our textwrap routine deals in slices.  This function will concat
    contiguous slices as an optimization so lookup performance is faster.
    It expects a sequence (probably a list) to add slice to or will extend
    the last slice of the sequence if it ends where the new slice begins. """
    if seq and seq[-1].stop == slc.start:
        seq[-1] = slice(seq[-1].start, slc.stop)
    else:
        seq.append(slc)


def _textwrap_slices(text, width, strip_leading_indent=False):
    """ Nearly identical to textwrap.wrap except this routine is a tad bit
    safer in its algo that textwrap.  I ran into some issues with textwrap
    output that make it unusable to this usecase as a baseline text wrapper.
    Further this utility returns slices instead of strings.  So the slices
    can be used to extract your lines manually. """
    if not isinstance(text, str):
        raise TypeError("Expected `str` type")
    chunks = (x for x in _textwrap_word_break.split(text) if x)
    remaining = width
    buf = []
    lines = [buf]
    whitespace = []
    whitespace_len = 0
    pos = 0
    try:
        chunk = next(chunks)
    except StopIteration:
        chunk = ''
    if not strip_leading_indent and is_whitespace(chunk):
        # Add leading indent for first line, but only up to one lines worth.
        chunk_len = len(chunk)
        if chunk_len >= width:
            _add_slice(buf, slice(0, width))
            buf = []
            lines.append(buf)
        else:
            _add_slice(buf, slice(0, chunk_len))
            remaining -= chunk_len
        pos = chunk_len
        try:
            chunk = next(chunks)
        except StopIteration:
            chunk = ''
    while True:
        avail_len = remaining - whitespace_len
        chunk_len = len(chunk)
        if chunk == '\n':
            buf = []
            lines.append(buf)
            whitespace = []
            whitespace_len = 0
            remaining = width
        elif is_whitespace(chunk):
            if buf:
                _add_slice(whitespace, slice(pos, pos + chunk_len))
                whitespace_len += chunk_len
        elif len(chunk) > avail_len:
            if not buf:
                # Must hard split the chunk.
                for x in whitespace:
                    _add_slice(buf, x)
                _add_slice(buf, slice(pos, pos + avail_len))
                chunk = chunk[avail_len:]
                pos += avail_len
            # Bump to next line without fetching the next chunk.
            buf = []
            lines.append(buf)
            whitespace = []
            whitespace_len = 0
            remaining = width
            continue
        else:
            if buf:
                remaining -= whitespace_len
                for x in whitespace:
                    _add_slice(buf, x)
            whitespace = []
            whitespace_len = 0
            _add_slice(buf, slice(pos, pos + chunk_len))
            remaining -= chunk_len
        pos += chunk_len
        try:
            chunk = next(chunks)
        except StopIteration:
            break
    return lines


class VTMLParser(html.parser.HTMLParser):
    """ Add some SGML style tag support for a few VT100 operations. """

    escape = ('&',)
    escape_setinal_base = 0xe2c6  # protected by PAU

    def __init__(self, *args, **kwargs):
        escape_tuples = enumerate(self.escape, self.escape_setinal_base)
        self.escape_map = tuple((chr(i), x) for i, x in escape_tuples)
        super().__init__(*args, **kwargs)

    def feed(self, data):
        """ We need to prevent insertion of some special HTML characters
        (entity refs and maybe more).  It's hard to prevent the state machine
        from blowing up with them in the data, so we temporarily replacing
        them with a reserved unicode value based on the PAU private space. """
        assert not self.closed
        for mark, special in self.escape_map:
            assert mark not in data
            data = data.replace(special, mark)
        super().feed(data)

    def reset(self):
        self.closed = False
        self.vbuf = VTMLBuffer()
        self.open_tags = []
        super().reset()

    def handle_starttag(self, tag, attrs):
        if tag not in TAGS:
            return self.handle_data(self.get_starttag_text())
        self.open_tags.append(tag)

    def handle_endtag(self, tag):
        if tag not in TAGS:
            return self.handle_data("</%s>" % tag)
        if self.open_tags[-1] != tag:
            raise SyntaxError("Bad close tag: %s; Expected: %s" % (tag,
                              self.open_tags[-1]))
        del self.open_tags[-1]
        self.vbuf.append_reset()

    def handle_data(self, data):
        if self.open_tags:
            for tag in self.open_tags:
                self.vbuf.append_tag(tag)
        for mark, special in self.escape_map:
            data = data.replace(mark, special)
        self.vbuf.append_str(data)

    def handle_entityref(self, name):
        raise RuntimeError("programmer error")

    def handle_charref(self, name):
        raise RuntimeError("programmer error")

    def unknown_decl(self, name):
        raise RuntimeError("programmer error")

    def handle_comment(self, data):
        raise RuntimeError("programmer error")

    def close(self):
        assert not self.closed
        super().close()
        if self.open_tags:
            self.vbuf.append_reset()
        self.closed = True

    def getvalue(self):
        assert self.closed
        return self.vbuf


@functools.total_ordering
class VTMLBuffer(object):
    """ A str-like object that has an adjusted length to compensate for
    nonvisual vt100 opcodes which do not occupy space in the output. """

    ops = enum.Enum('ops', 'reset tag str')
    _reset_opcode = '\033[0m'

    @classmethod
    def new(cls, *args, **kwargs):
        """ Subclass friendly factory for getting a new buffer. """
        return cls(*args, **kwargs)

    @classmethod
    def from_buffers(cls, buffers):
        """ Join all argument buffers into a new unified buffer object. """
        new = cls()
        for obj in buffers:
            new.extend(obj)
        return new

    def __init__(self, value=None):
        self._values = []
        if value is not None:
            if isinstance(value, str):
                self.append_str(value)
            elif isinstance(value, VTMLBuffer):
                self.extend(value)
            else:
                raise TypeError("Init value must be `str` or `VTMLBuffer`")

    def __len__(self):
        return len(self.text())

    def __str__(self):
        buf = []
        for op, val in self._values:
            if op == self.ops.str:
                buf.append(val)
            elif op == self.ops.tag:
                buf.append('\033[%dm' % TAGS[val])
            elif op == self.ops.reset:
                buf.append(self._reset_opcode)
            else:
                raise ValueError("invalid op: %r" % (op,))
        return ''.join(buf)

    def __repr__(self):
        return repr(str(self))

    def __eq__(self, other):
        return str(self) == str(other)

    def __lt__(self, other):
        return str(self) < str(other)

    def __contains__(self, other):
        return other in self.text()

    def __format__(self, fmt):
        """ Add support for re-embedded VTML via the `vtml` specifier in a
        `str.format` argument. E.g.
            >>> words = shellish.vtmlrender('<u>underlined words')
            >>> '<b>Make bold: {:vtml}, thanks</b>'.format(words)
            '<b>Make bold: <u>underlined words</u>, thanks</b>'
        """
        if fmt == 'vtml':
            buf = []
            tag_stack = []
            for op, val in self._values:
                if op == self.ops.str:
                    buf.append(val)
                elif op == self.ops.tag:
                    tag_stack.append(val)
                    buf.append('<%s>' % val)
                elif op == self.ops.reset:
                    if tag_stack:
                        for x in reversed(tag_stack):
                            buf.append('</%s>' % x)
                        del tag_stack[:]
                else:
                    raise ValueError("invalid op: %r" % (op,))
            return ''.join(buf)
        else:
            return str(self)

    def __add__(self, other):
        if isinstance(other, str):
            other = self.new(other)
        elif not isinstance(other, VTMLBuffer):
            raise TypeError("Invalid concatenation type: %s" % type(other))
        new = self.copy()
        new.extend(other)
        return new

    def __iadd__(self, other):
        if isinstance(other, str):
            self.append_str(other)
        elif isinstance(other, VTMLBuffer):
            self.extend(other)
        else:
            raise TypeError("Invalid concatenation type: %s" % type(other))
        return self

    def __radd__(self, other):
        if isinstance(other, str):
            return other + str(self)
        elif isinstance(other, VTMLBuffer):
            return other + self
        else:
            raise TypeError("Invalid concatenation type: %s" % type(other))

    def __mul__(self, factor):
        if not isinstance(factor, int):
            raise TypeError('Expected `int` type factor')
        new = self.copy()
        new._values *= factor
        return new

    __rmul__ = __mul__

    def __imul__(self, factor):
        if not isinstance(factor, int):
            raise TypeError('Expected `int` type factor')
        self._values *= factor
        return self

    def __getitem__(self, key):
        """ Support for slicing and indexing.  Results are always a new
        VTMLBuffer copy. """
        visual_len = len(self)
        if isinstance(key, slice):
            if key.step is not None:
                raise TypeError("`step` is not supported")
            start = key.start or 0
            if start < 0:
                start = visual_len + start
            stop = key.stop if key.stop is not None else visual_len
            if stop < 0:
                stop = visual_len + stop
        else:
            start = key
            if start < 0:
                start = visual_len + start
            if not 0 <= start < visual_len:
                raise IndexError('Index out of range')
            stop = start + 1
        remaining = max(stop - start, 0)
        new = self.new()
        op_active = False
        pos = 0
        for op, val in self._values:
            if not remaining:
                break
            elif op == self.ops.tag:
                new.append_tag(val)
                op_active = True
            elif op == self.ops.reset:
                new.append_reset()
                op_active = False
            elif op == self.ops.str:
                snip = val[start - pos:] if start > pos else val
                pos += len(val)
                if snip:
                    fragment = snip[:remaining]
                    remaining -= len(fragment)
                    new.append_str(fragment)
            else:
                raise RuntimeError("Invalid op type")
        if op_active:
            new.append_reset()
        return new

    def copy(self):
        return self.new(self)

    def append_reset(self):
        self._values.append((self.ops.reset, None))

    def append_tag(self, tag):
        self._values.append((self.ops.tag, tag))

    def append_str(self, value):
        self._values.append((self.ops.str, value))

    def extend(self, buf):
        if not isinstance(buf, VTMLBuffer):
            raise TypeError("Expected `VTMLBuffer`")
        self._values.extend(buf._values)

    def _promiscuous_extend(self, buf, other):
        """ Extend that supports `VTMLBuffer` and `str`. """
        try:
            buf.extend(other)
        except TypeError:
            if isinstance(other, str):
                buf.append_str(other)
            else:
                raise TypeError("Expected `VTMLBuffer` or `str`. Got `%s`" %
                                type(other))

    def join(self, buffers):
        """ Same interface as b''.join and ''.join. Supports upconversion of
        `str` types too. """
        output = self.new()
        bufiter = iter(buffers)
        try:
            self._promiscuous_extend(output, next(bufiter))
        except StopIteration:
            return output
        for buf in bufiter:
            output.extend(self)
            self._promiscuous_extend(output, buf)
        return output

    def text(self):
        """ Return just the text content of this string without opcodes. """
        return ''.join(val for op, val in self._values if op == self.ops.str)

    def plain(self):
        """ Similar to `text` but returns valid VTMLBuffer instance. """
        new = self.new()
        for op, val in self._values:
            if op == self.ops.str:
                new.append_str(val)
        return new

    def clip(self, length, cliptext=''):
        """ Clip text for lines exceeding a particular length.  Newlines and
        trailing are also removed. """
        if length < 0:
            raise ValueError("Negative clip invalid")
        cliplen = len(cliptext)
        if length < cliplen:
            raise ValueError("Clip length too small: %d < %d" % (length,
                             cliplen))
        text = self.text()
        first = text.splitlines()[0] if text else text
        stripped = first.rstrip()
        clipping = len(first) != len(text) or len(stripped) > length
        adj_length = min(len(stripped), length - (cliplen if clipping else 0))
        new = self[:adj_length]
        if clipping and cliptext:
            new.append_str(cliptext)
        return new

    def wrap(self, width, **options):
        """ Text wrapping similar to textwrap.wrap but protects vt escape
        sequences by returning a list of VTMLBuffer objects. """
        if width <= 0:
            raise ValueError("Invalid wrap width: %d" % width)
        slices = _textwrap_slices(self.text(), width, **options)
        return [self.from_buffers(self[s] for s in line_slices)
                for line_slices in slices]

    def ljust(self, width, fillchar=' '):
        new = self.copy()
        if width > len(self):
            new.append_str(fillchar * (width - len(self)))
        return new

    def rjust(self, width, fillchar=' '):
        new = self.new()
        if width > len(self):
            new.append_str(fillchar * (width - len(self)))
        new.extend(self)
        return new

    def center(self, width, fillchar=' '):
        """ Center strings so uneven padding always favors trailing pad.  When
        centering clumps of text this produces better results than str.center
        which alternates which side uneven padding occurs on. """
        if width > len(self):
            padlen = width - len(self)
            leftlen = padlen // 2
            rightlen = padlen - leftlen
            new = self.new()
            new.append_str(fillchar * leftlen)
            new.extend(self)
            new.append_str(fillchar * rightlen)
            return new
        else:
            return self.copy()

    def rstrip(self):
        """ Removing trailing whitespace. """
        removals = []
        i = len(self._values)
        for op, val in reversed(self._values):
            i -= 1
            if op == self.ops.str:
                if is_whitespace(val):
                    removals.append(i)
                else:
                    break
        copy = self.copy()
        for i in removals:
            del copy._values[i]
        return copy

    def startswith(self, other):
        return self.text().startswith(other)

    def endswith(self, other):
        return self.text().endswith(other)

    def split(self, sep=' ', maxsplit=None):
        if not sep:
            raise ValueError("empty separator")
        splits = []
        pos = 0
        text = self.text()
        sep_len = len(sep)
        while maxsplit is None or len(splits) < maxsplit:
            try:
                end = text.index(sep, pos)
            except ValueError:
                break
            splits.append((pos, end))
            pos = end + sep_len
        splits.append((pos, None))
        return [self[start:end] for start, end in splits]
        if splits:
            return [self[start:end] for start, end in splits]
        else:
            return [self.copy()]


def vtmlrender(vtmarkup, plain=None, strict=False, vtmlparser=VTMLParser()):
    """ Look for vt100 markup and render vt opcodes into a VTMLBuffer. """
    if isinstance(vtmarkup, VTMLBuffer):
        return vtmarkup.plain() if plain else vtmarkup
    try:
        vtmlparser.feed(vtmarkup)
        vtmlparser.close()
    except:
        if strict:
            raise
        buf = VTMLBuffer()
        buf.append_str(str(vtmarkup))
        return buf
    else:
        buf = vtmlparser.getvalue()
        return buf.plain() if plain else buf
    finally:
        vtmlparser.reset()


def vtmlprint(*values, plain=None, strict=None, **options):
    """ Follow normal print() signature but look for vt100 codes for richer
    output. """
    print(*[vtmlrender(x, plain=plain, strict=strict) for x in values],
          **options)
