
import itertools
import unittest
from shellish import rendering as R


class VTMLStringTests(unittest.TestCase):

    def test_vtstr_overclip_plain(self):
        startval = 'A' * 10
        s = R.vtmlrender(startval)
        self.assertEqual(s.clip(11), startval)
        self.assertEqual(s.clip(11).text(), startval)
        self.assertEqual(s.clip(20), startval)
        self.assertEqual(s.clip(20).text(), startval)

    def test_vtstr_noclip_plain(self):
        startval = 'A' * 10
        s = R.vtmlrender(startval)
        self.assertEqual(s.clip(10), startval)
        self.assertEqual(s.clip(10).text(), startval)

    def test_vtstr_underclip_plain(self):
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

    def test_vtstr_overclip_vtml(self):
        startval = 'A' * 10
        s = R.vtmlrender('<b>%s</b>' % startval)
        self.assertEqual(s.clip(11).text(), startval)
        self.assertEqual(s.clip(20).text(), startval)
        self.assertEqual(s.clip(11), s)
        self.assertEqual(s.clip(20), s)

    def test_vtstr_noclip_vtml(self):
        startval = 'A' * 10
        s = R.vtmlrender('<b>%s</b>' % startval)
        self.assertEqual(s.clip(10).text(), startval)
        self.assertEqual(s.clip(10), s)

    def test_vtstr_underclip_vtml(self):
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

    def test_vtstr_underclip_vtml_reset(self):
        s = R.vtmlrender('<b>%s</b>' % 'AAAA')
        self.assertTrue(str(s.clip(2)).endswith('\033[0m'))

    def test_vtstr_overclip_with_cliptextt(self):
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

    def test_vtstr_underclip_with_cliptextt(self):
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
        ab = R.vtmlrender('aaaaBBBB')
        self.assertEqual(a+b, ab)
        self.assertEqual(str(a+b), str(ab))

    def test_iadd_same_type(self):
        a1 = R.vtmlrender('aaaa')
        a1 += R.vtmlrender('BBBB')
        a2 = R.vtmlrender('aaaaBBBB')
        self.assertEqual(a1, a2)

    def test_add_str_type(self):
        a = R.vtmlrender('aaaa')
        b = 'BBBB'
        ab = R.vtmlrender('aaaaBBBB')
        self.assertEqual(a+b, ab)
        self.assertEqual(str(a+b), str(ab))

    def test_iadd_str_type(self):
        a1 = R.vtmlrender('aaaa')
        a1 += 'BBBB'
        a2 = R.vtmlrender('aaaaBBBB')
        self.assertEqual(a1, a2)

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
            self.assertIn('\033', valid, 'sanity test to validate next portion')
            ends = next(perms)  # makes for bad closes
            buf = ["<%s>asdf</%s>" % (x, y) for x, y in zip(starts, ends)]
            line = ''.join(buf)
            ugly = str(R.vtmlrender(line + suffix, strict=True))
            self.assertIn(valid, ugly)
            self.assertEqual(ugly, line + valid, 'partial conv did not work')

    def test_pound(self):
        for t in ('a#bc', 'a&#1;'):
            self.assertEqual(R.vtmlrender(t, strict=True), t)


class HTMLConversion(unittest.TestCase):

    a_format = '<blue><u>%s</u></blue>'

    def test_empty(self):
        R.htmlrender('')

    def test_parity(self):
        for tag in ('b', 'u'):
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
