
import itertools
import unittest
from shellish import rendering as R


class VTMLBufferTests(unittest.TestCase):

    def test_overclip_plain(self):
        startval = 'A' * 10
        s = R.vtmlrender(startval)
        self.assertEqual(s.clip(11), startval)
        self.assertEqual(s.clip(11).text(), startval)
        self.assertEqual(s.clip(20), startval)
        self.assertEqual(s.clip(20).text(), startval)

    def test_noclip_plain(self):
        startval = 'A' * 10
        s = R.vtmlrender(startval)
        self.assertEqual(s.clip(10), startval)
        self.assertEqual(s.clip(10).text(), startval)

    def test_underclip_plain(self):
        startval = 'A' * 10
        s = R.vtmlrender(startval)
        self.assertEqual(s.clip(9), startval[:9])
        self.assertEqual(s.clip(9).text(), startval[:9])
        self.assertEqual(s.clip(4), startval[:4])
        self.assertEqual(s.clip(4).text(), startval[:4])
        self.assertEqual(s.clip(1), startval[:1])
        self.assertEqual(s.clip(1).text(), startval[:1])
        self.assertEqual(s.clip(0), '')
        self.assertEqual(s.clip(0).text(), '')
        self.assertRaises(ValueError, s.clip, -10)

    def test_overclip_vtml(self):
        startval = 'A' * 10
        s = R.vtmlrender('<b>%s</b>' % startval)
        self.assertEqual(s.clip(11).text(), startval)
        self.assertEqual(s.clip(20).text(), startval)
        self.assertEqual(s.clip(11), s)
        self.assertEqual(s.clip(20), s)

    def test_noclip_vtml(self):
        startval = 'A' * 10
        s = R.vtmlrender('<b>%s</b>' % startval)
        self.assertEqual(s.clip(10).text(), startval)
        self.assertEqual(s.clip(10), s)

    def test_underclip_vtml(self):
        startval = 'A' * 10
        s = R.vtmlrender('<b>%s</b>' % startval)
        self.assertEqual(s.clip(9).text(), startval[:9])
        self.assertEqual(str(s.clip(9)).count('A'), 9)
        self.assertEqual(s.clip(4).text(), startval[:4])
        self.assertEqual(str(s.clip(4)).count('A'), 4)
        self.assertEqual(s.clip(1).text(), startval[:1])
        self.assertEqual(str(s.clip(1)).count('A'), 1)
        self.assertEqual(s.clip(0).text(), '')
        self.assertEqual(s.clip(0), '')
        self.assertRaises(ValueError, s.clip, -10)

    def test_underclip_vtml_reset(self):
        s = R.vtmlrender('<b>%s</b>' % 'AAAA')
        self.assertTrue(str(s.clip(2)).endswith('\033[0m'))

    def test_overclip_with_cliptextt(self):
        startval = 'A' * 10
        s = R.vtmlrender(startval)
        self.assertEqual(s.clip(12, '.'), startval)
        self.assertEqual(s.clip(11, '.'), startval)
        self.assertEqual(s.clip(10, '.'), startval)
        self.assertEqual(s.clip(12, '..'), startval)
        self.assertEqual(s.clip(11, '..'), startval)
        self.assertEqual(s.clip(10, '..'), startval)
        self.assertEqual(s.clip(12, '...'), startval)
        self.assertEqual(s.clip(11, '...'), startval)
        self.assertEqual(s.clip(10, '...'), startval)

    def test_underclip_with_cliptextt(self):
        startval = 'A' * 10
        s = R.vtmlrender(startval)
        self.assertEqual(s.clip(9, '.'), startval[:8] + '.')
        self.assertEqual(s.clip(8, '.'), startval[:7] + '.')
        self.assertEqual(s.clip(7, '.'), startval[:6] + '.')
        self.assertEqual(s.clip(9, '..'), startval[:7] + '..')
        self.assertEqual(s.clip(8, '..'), startval[:6] + '..')
        self.assertEqual(s.clip(7, '..'), startval[:5] + '..')
        self.assertEqual(s.clip(9, '...'), startval[:6] + '...')
        self.assertEqual(s.clip(8, '...'), startval[:5] + '...')
        self.assertEqual(s.clip(7, '...'), startval[:4] + '...')
        self.assertEqual(s.clip(6, '...'), startval[:3] + '...')

    def test_clip_strip(self):
        self.assertEqual(R.vtmlrender('\n').clip(10, '!').text(), '!')
        self.assertEqual(R.vtmlrender(' \n').clip(10, '!').text(), '!')
        self.assertEqual(R.vtmlrender(' ').clip(10, '!').text(), '')
        self.assertEqual(R.vtmlrender('A\n').clip(10, '!').text(), 'A!')
        self.assertEqual(R.vtmlrender('A\nB').clip(10, '!').text(), 'A!')
        self.assertEqual(R.vtmlrender('A\n').clip(1, '!').text(), '!')
        self.assertEqual(R.vtmlrender('A ').clip(1, '!').text(), 'A')
        self.assertEqual(R.vtmlrender('A  ').clip(1, '!').text(), 'A')
        self.assertEqual(R.vtmlrender('A \n').clip(1, '!').text(), '!')
        self.assertEqual(R.vtmlrender('A \n ').clip(1, '!').text(), '!')
        self.assertEqual(R.vtmlrender('A\n').clip(2, '!').text(), 'A!')
        self.assertEqual(R.vtmlrender('A ').clip(2, '!').text(), 'A')
        self.assertEqual(R.vtmlrender('A  ').clip(2, '!').text(), 'A')
        self.assertEqual(R.vtmlrender('A \n').clip(2, '!').text(), 'A!')
        self.assertEqual(R.vtmlrender('A \n ').clip(2, '!').text(), 'A!')
        self.assertEqual(R.vtmlrender('    ').clip(5, '!').text(), '')
        self.assertEqual(R.vtmlrender('    ').clip(4, '!').text(), '')
        self.assertEqual(R.vtmlrender('    ').clip(3, '!').text(), '')
        self.assertEqual(R.vtmlrender('    ').clip(2, '!').text(), '')
        self.assertEqual(R.vtmlrender('    ').clip(1, '!').text(), '')

    def test_clip_empty(self):
        self.assertEqual(R.vtmlrender('').clip(10, '!').text(), '')

    def test_wrap_empty(self):
        buf = R.vtmlrender('')
        self.assertListEqual(buf.wrap(10), [''])

    def test_wrap_identity(self):
        buf = R.vtmlrender('abcdefgh')
        self.assertIsInstance(buf.wrap(10), list)
        self.assertIsInstance(buf.wrap(8), list)
        self.assertIsInstance(buf.wrap(1), list)
        self.assertRaises(ValueError, buf.wrap, -1)
        self.assertRaises(ValueError, buf.wrap, 0)
        self.assertRaises(ValueError, buf.wrap, -2)
        self.assertRaises(ValueError, buf.wrap, -8)
        self.assertRaises(ValueError, buf.wrap, -10)

    def test_wrap_boundries_packed_stronly(self):
        buf = R.vtmlrender('abcdefgh')
        self.assertListEqual(buf.wrap(10), ['abcdefgh'])
        self.assertListEqual(buf.wrap(8), ['abcdefgh'])
        self.assertListEqual(buf.wrap(7), ['abcdefg', 'h'])
        self.assertListEqual(buf.wrap(2), ['ab', 'cd', 'ef', 'gh'])
        self.assertListEqual(buf.wrap(1), list('abcdefgh'))

    def test_wrap_boundries_hypens_stronly(self):
        buf = R.vtmlrender('abcd-efgh')
        self.assertListEqual(buf.wrap(10), ['abcd-efgh'])
        self.assertListEqual(buf.wrap(8), ['abcd-', 'efgh'])

    def test_wrap_whitespace_stronly(self):
        buf = R.vtmlrender('abcd efgh')
        self.assertListEqual(buf.wrap(10), ['abcd efgh'])
        self.assertListEqual(buf.wrap(8), ['abcd', 'efgh'])
        self.assertListEqual(buf.wrap(7), ['abcd', 'efgh'])
        self.assertListEqual(buf.wrap(2), ['ab', 'cd', 'ef', 'gh'])
        self.assertListEqual(buf.wrap(1), list('abcdefgh'))

    def test_wrap_multi_whitespace_stronly(self):
        buf = R.vtmlrender(' A BB  CCC  DDDD EEEEE ')
        self.assertListEqual(buf.wrap(10), [' A BB  CCC', 'DDDD EEEEE'])
        self.assertListEqual(buf.wrap(8), [' A BB', 'CCC', 'DDDD', 'EEEEE'])
        self.assertListEqual(buf.wrap(7), [' A BB', 'CCC', 'DDDD', 'EEEEE'])
        self.assertListEqual(buf.wrap(2), [
            ' A', 'BB', 'CC', 'C', 'DD', 'DD', 'EE', 'EE', 'E'])
        self.assertListEqual(buf.wrap(1), [
            ' ', 'A', 'B', 'B', 'C', 'C', 'C', 'D', 'D', 'D', 'D', 'E', 'E',
            'E', 'E', 'E'])

    def test_wrap_overflow_whitespace_stronly(self):
        buf = R.vtmlrender('        A BB  ')
        self.assertListEqual(buf.wrap(20), ['        A BB'])
        self.assertListEqual(buf.wrap(5), ['     ', 'A BB'])
        self.assertListEqual(buf.wrap(3), ['   ', 'A', 'BB'])
        self.assertListEqual(buf.wrap(2), ['  ', 'A', 'BB'])
        buf = R.vtmlrender('        A BB         ')
        self.assertListEqual(buf.wrap(20), ['        A BB'])
        self.assertListEqual(buf.wrap(5), ['     ', 'A BB'])
        self.assertListEqual(buf.wrap(3), ['   ', 'A', 'BB'])
        self.assertListEqual(buf.wrap(2), ['  ', 'A', 'BB'])
        buf = R.vtmlrender('        A             BB         ')
        self.assertListEqual(buf.wrap(30), ['        A             BB'])
        self.assertListEqual(buf.wrap(5), ['     ', 'A', 'BB'])
        self.assertListEqual(buf.wrap(3), ['   ', 'A', 'BB'])
        self.assertListEqual(buf.wrap(2), ['  ', 'A', 'BB'])

    def test_wrap_newlines(self):
        for width in 1, 2, 80:
            with self.subTest('width=%d' % width):
                buf = R.vtmlrender('A\nB')
                self.assertListEqual(buf.wrap(width), ['A', 'B'])
                buf = R.vtmlrender('A\n\nB')
                self.assertListEqual(buf.wrap(width), ['A', '', 'B'])
                buf = R.vtmlrender('A\n\n\nB')
                self.assertListEqual(buf.wrap(width), ['A', '', '', 'B'])
                buf = R.vtmlrender('A\n\n\nB')
                self.assertListEqual(buf.wrap(width), ['A', '', '', 'B'])
                buf = R.vtmlrender('A\n   B')
                self.assertListEqual(buf.wrap(width), ['A', 'B'])
                buf = R.vtmlrender('A    \n   B')
                self.assertListEqual(buf.wrap(width), ['A', 'B'])
                buf = R.vtmlrender('A    \nB')
                self.assertListEqual(buf.wrap(width), ['A', 'B'])

    def test_wrap_no_indent(self):
        buf = R.vtmlrender('  A\nB')
        self.assertListEqual(buf.wrap(20, strip_leading_indent=True),
                             ['A', 'B'])

    @unittest.skip
    def test_wrap_expand_tabs(self):
        buf = R.vtmlrender('A\tB')
        self.assertListEqual(buf.wrap(20), ['A    B'])
        self.assertListEqual(buf.wrap(3), ['A', 'B'])
        self.assertListEqual(buf.wrap(2), ['A', 'B'])
        self.assertListEqual(buf.wrap(20, expand_tabs=False), ['A\tB'])
        self.assertListEqual(buf.wrap(3, expand_tabs=False), ['A\tB'])
        self.assertListEqual(buf.wrap(2, expand_tabs=False), ['A', 'B'])

    def test_bad_data(self):
        bad = [
            None,
            0,
            1,
            ['asdf', 'asdf'],
            [None, None],
            '<>asdf',
            '</b>asdf</notit>',
        ]
        for x in bad:
            self.assertEqual(R.vtmlrender(x), x)

    def test_ordering(self):
        self.assertGreater(R.vtmlrender('bbbb'), R.vtmlrender('aaaa'))
        self.assertLess(R.vtmlrender('aaaa'), R.vtmlrender('bbbb'))
        self.assertGreaterEqual(R.vtmlrender('bbbb'), R.vtmlrender('aaaa'))
        self.assertGreaterEqual(R.vtmlrender('aaaa'), R.vtmlrender('aaaa'))
        self.assertLessEqual(R.vtmlrender('aaaa'), R.vtmlrender('bbbb'))
        self.assertLessEqual(R.vtmlrender('aaaa'), R.vtmlrender('aaaa'))
        self.assertEqual(R.vtmlrender('aaaa'), R.vtmlrender('aaaa'))

    def test_add_same_type(self):
        a = R.vtmlrender('aaaa')
        b = R.vtmlrender('BBBB')
        c = a + b
        self.assertIsNot(c, a)
        self.assertIsNot(c, b)
        self.assertEqual(c, R.vtmlrender('aaaaBBBB'))
        self.assertEqual(str(c), 'aaaaBBBB')

    def test_add_str_type(self):
        a = R.vtmlrender('aaaa')
        b = 'BBBB'
        c = a + b
        self.assertIsNot(c, a)
        self.assertEqual(c, R.vtmlrender('aaaaBBBB'))
        self.assertEqual(str(c), 'aaaaBBBB')

    def test_iadd_same_type(self):
        a1 = a1_save = R.vtmlrender('aaaa')
        a1 += R.vtmlrender('BBBB')
        self.assertIs(a1, a1_save)
        self.assertEqual(a1, R.vtmlrender('aaaaBBBB'))
        self.assertEqual(str(a1), 'aaaaBBBB')

    def test_iadd_str_type(self):
        a1 = a1_save = R.vtmlrender('aaaa')
        a1 += 'BBBB'
        self.assertIs(a1, a1_save)
        self.assertEqual(a1, R.vtmlrender('aaaaBBBB'))
        self.assertEqual(str(a1), 'aaaaBBBB')

    def test_right_add_str_type(self):
        a = R.vtmlrender('aaaa')
        b = 'BBBB' + a
        self.assertEqual(b, 'BBBBaaaa')
        self.assertIsInstance(b, str)

    def test_add_ident(self):
        a1 = R.vtmlrender('aaaa')
        a2 = a1 + 'BBBB'
        self.assertIsNot(a1, a2)
        self.assertNotEqual(a1, a2)

    def test_iadd_unsupport_type(self):
        a1 = R.vtmlrender('foo')
        self.assertRaises(TypeError, lambda: a1 + 1)
        self.assertRaises(TypeError, lambda: a1 + b'bar')

    def test_amp_tail_single_char(self):
        """ Without a workaround this hits a bug in HTMLParser. """
        t = 'a&b'
        self.assertEqual(R.vtmlrender(t, strict=True), t)

    def test_amp_tail_double_char(self):
        t = 'a&bc'
        self.assertEqual(R.vtmlrender(t, strict=True), t)

    def test_amp_tail(self):
        t = 'a&'
        self.assertEqual(R.vtmlrender(t, strict=True), t)

    def test_amp_normal(self):
        for t in ('a&gt;', '&lt;', '&ltss;', '&;', '&abc;<other>'):
            self.assertEqual(R.vtmlrender(t, strict=True), t)

    def test_wrong_tag_tolerance(self):
        bad = ('foobar', 'foo', 'bar')
        perms = itertools.permutations(bad)
        for starts in perms:
            suffix = '<b>valid</b>'
            valid = str(R.vtmlrender(suffix, strict=True))
            self.assertIn('\033', valid, 'test to validate next portion')
            ends = next(perms)  # makes for bad closes
            buf = ["<%s>asdf</%s>" % (x, y) for x, y in zip(starts, ends)]
            line = ''.join(buf)
            ugly = str(R.vtmlrender(line + suffix, strict=True))
            self.assertIn(valid, ugly)
            self.assertEqual(ugly, line + valid, 'partial conv did not work')

    def test_pound(self):
        for t in ('a#bc', 'a&#1;'):
            self.assertEqual(R.vtmlrender(t, strict=True), t)

    def test_multiply(self):
        a = R.vtmlrender('A')
        self.assertEqual(a * 2, R.vtmlrender('AA'))
        self.assertEqual(a * 3, R.vtmlrender('AAA'))
        self.assertEqual((a * 3).text(), 'AAA')
        a = R.vtmlrender('AB')
        self.assertEqual(a * 2, R.vtmlrender('ABAB'))
        self.assertEqual(a * 3, R.vtmlrender('ABABAB'))
        self.assertEqual((a * 3).text(), 'ABABAB')
        self.assertRaises(TypeError, lambda: 1.5 * a)
        self.assertRaises(TypeError, lambda: '' * a)
        self.assertRaises(TypeError, lambda: a * a)

    def test_inplace_multiply(self):
        a = a_save = R.vtmlrender('A ')
        a *= 3
        self.assertIs(a, a_save)
        self.assertEqual(a, R.vtmlrender('A A A '))
        self.assertRaises(TypeError, lambda: 1.5 * a)
        self.assertRaises(TypeError, lambda: '' * a)
        self.assertRaises(TypeError, lambda: a * a)

    def test_right_multiply(self):
        a = R.vtmlrender('A')
        self.assertEqual(2 * a, R.vtmlrender('AA'))
        self.assertEqual(3 * a, R.vtmlrender('AAA'))
        self.assertEqual((3 * a).text(), 'AAA')
        a = R.vtmlrender('AB')
        self.assertEqual(2 * a, R.vtmlrender('ABAB'))
        self.assertEqual(3 * a, R.vtmlrender('ABABAB'))
        self.assertEqual((3 * a).text(), 'ABABAB')
        self.assertRaises(TypeError, lambda: 1.5 * a)
        self.assertRaises(TypeError, lambda: '' * a)
        self.assertRaises(TypeError, lambda: a * a)

    def test_left_justify(self):
        a = R.vtmlrender('A')
        self.assertEqual(a.ljust(0), 'A')
        self.assertEqual(a.ljust(1), 'A')
        self.assertEqual(a.ljust(2), 'A ')
        self.assertEqual(a.ljust(3), 'A  ')

    def test_startswith(self):
        abc = R.vtmlrender('abc')
        self.assertIs(abc.startswith(''), True)
        self.assertIs(abc.startswith('a'), True)
        self.assertIs(abc.startswith('ab'), True)
        self.assertIs(abc.startswith('abc'), True)
        self.assertIs(abc.startswith('A'), False)
        self.assertIs(abc.startswith('ABC'), False)
        self.assertIs(abc.startswith('ABCD'), False)
        a = R.vtmlrender('<b>a')
        b = R.vtmlrender('b')
        c = R.vtmlrender('<u>c')
        self.assertIs((a + b + c).startswith('abc'), True)
        self.assertIs((a + b + c).startswith(''), True)
        self.assertIs((a + b + c).startswith('<b>'), False)
        self.assertIs((a + b + c).startswith('A'), False)
        self.assertIs((a + b + c).startswith('ABC'), False)
        self.assertIs((a + b + c).startswith('ABCD'), False)

    def test_endswith(self):
        abc = R.vtmlrender('abc')
        self.assertIs(abc.endswith(''), True)
        self.assertIs(abc.endswith('c'), True)
        self.assertIs(abc.endswith('bc'), True)
        self.assertIs(abc.endswith('abc'), True)
        self.assertIs(abc.endswith('C'), False)
        self.assertIs(abc.endswith('ABC'), False)
        self.assertIs(abc.endswith('ABCD'), False)
        abc = R.vtmlrender('<b>a')
        abc += R.vtmlrender('b')
        abc += R.vtmlrender('<u>c</u>')
        self.assertIs(abc.endswith('abc'), True)
        self.assertIs(abc.endswith(''), True)
        self.assertIs(abc.endswith('</u>'), False)
        self.assertIs(abc.endswith('C'), False)
        self.assertIs(abc.endswith('ABC'), False)
        self.assertIs(abc.endswith('ABCD'), False)

    def test_in(self):
        abc = R.vtmlrender('abc')
        self.assertIn('', abc)
        self.assertIn('a', abc)
        self.assertIn('abc', abc)
        self.assertIn('abc', abc)
        self.assertNotIn('A', abc)
        self.assertNotIn('ABC', abc)
        self.assertNotIn('ABCD', abc)
        abc = R.vtmlrender('<b>a') + R.vtmlrender('bc') + R.vtmlrender('<u>c')
        self.assertIn('a', abc)
        self.assertIn('abc', abc)
        self.assertNotIn('<b>', abc)
        self.assertNotIn('A', abc)
        self.assertNotIn('ABC', abc)
        self.assertNotIn('ABCD', abc)
        self.assertNotIn('abcd', abc)

    def test_split_maxsplit(self):
        ref = 'abc ABC xyz XYZ'
        vs = R.vtmlrender(ref)
        self.assertListEqual(vs.split(), ref.split(' '))
        for i in range(6):
            with self.subTest(i):
                self.assertListEqual(vs.split(maxsplit=i), ref.split(' ', i))

    def test_split_leading(self):
        for ref in (' ', ' abc', '  ', '  abc'):
            vs = R.vtmlrender(ref)
            self.assertListEqual(vs.split(), ref.split(' '))

    def test_split_trailing(self):
        for ref in ('abc ', 'abc  ', ' abc ', '  abc  '):
            vs = R.vtmlrender(ref)
            self.assertListEqual(vs.split(), ref.split(' '))

    def test_split_notfound(self):
        ref = 'abc'
        vs = R.vtmlrender(ref)
        self.assertListEqual(vs.split('D'), ref.split('D'))
        self.assertListEqual(vs.split('abcd'), ref.split('abcd'))
        self.assertListEqual(vs.split('bcd'), ref.split('bcd'))

    def test_split_multichar(self):
        for ref in ('abcGAPABC', 'abcGAP', 'GAPabc', 'abGAPABGAP',
                    'aGAPbGAPc'):
            vs = R.vtmlrender(ref)
            self.assertListEqual(vs.split('GAP'), ref.split('GAP'))


class HTMLConversion(unittest.TestCase):

    a_format = '<blue><u>%s</u></blue>'

    def test_empty(self):
        R.htmlrender('')

    def test_parity(self):
        for tag in ('b', 'u', 'i'):
            markup = '<%s>stuff</%s>' % (tag, tag)
            self.assertEqual(R.html2vtml(markup), markup)

    def test_noop(self):
        self.assertEqual(R.html2vtml('<script>nope</script>'), '')

    def test_strip(self):
        self.assertEqual(R.html2vtml('<script>nope</script>'), '')
        self.assertEqual(R.html2vtml('before<script>nope</script>after'),
                         'beforeafter')

    def test_icase_tag(self):
        t = R.vtmlrender('<b>foo</b>')
        self.assertEqual(R.htmlrender('<B>foo</b>'), t)
        self.assertEqual(R.htmlrender('<B>foo</B>'), t)
        self.assertEqual(R.htmlrender('<b>foo</B>'), t)

    def test_a_tag_no_href(self):
        self.assertEqual(R.html2vtml('<a>foo</a>'), self.a_format % 'foo')

    def test_empty_href(self):
        self.assertEqual(R.html2vtml('<a href>foo</a>'), self.a_format % 'foo')

    def test_unquoted_href(self):
        self.assertEqual(R.html2vtml('<a href=link.here>foo</a>'),
                         self.a_format % 'foo (link.here)')

    def test_quoted_href(self):
        self.assertEqual(R.html2vtml('<a href="link.here">foo</a>'),
                         self.a_format % 'foo (link.here)')
        self.assertEqual(R.html2vtml("<a href='link.here'>foo</a>"),
                         self.a_format % 'foo (link.here)')

    def test_icase_href(self):
        for x in ('HREF', 'Href', 'hreF', 'href'):
            self.assertEqual(R.html2vtml('<a %s="link.here">foo</a>' % x),
                             self.a_format % 'foo (link.here)', x)
            self.assertEqual(R.html2vtml('<A %s="link.here">foo</a>' % x),
                             self.a_format % 'foo (link.here)')
            self.assertEqual(R.html2vtml('<A %s="link.here">foo</A>' % x),
                             self.a_format % 'foo (link.here)')
            self.assertEqual(R.html2vtml('<a %s="link.here">foo</A>' % x),
                             self.a_format % 'foo (link.here)')


class MDConversion(unittest.TestCase):

    def test_empty(self):
        R.mdrender('')

    def test_bold(self):
        self.assertEqual(R.mdrender('**foo**'), R.vtmlrender('\n<b>foo</b>\n'))
        self.assertEqual(R.mdrender('__foo__'), R.vtmlrender('\n<b>foo</b>\n'))
