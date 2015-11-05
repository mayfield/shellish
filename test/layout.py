
import argparse
import io
import itertools
import os
import statistics
import sys
import unittest
from shellish import layout as L


def calc_table(*columns, width=100, data=None, flex=False):
    t = L.Table(columns=columns, width=width, flex=flex, column_padding=0)
    return t.make_renderer(data or []).widths


def fileredir(call, *args, **kwargs):
    """ Override `file` with stringio object and return a tuple of a function
    to get the output and the instantiated callable. """
    file = io.StringIO()
    output = lambda: file.getvalue().splitlines()
    return output, call(*args, file=file, **kwargs)


class TabularUnflex(unittest.TestCase):

    def test_only_pct(self):
        widths = calc_table(.10, .40, .50)
        self.assertEqual(widths, [10, 40, 50])

    def test_only_fixed(self):
        widths = calc_table(10, 40, 50)
        self.assertEqual(widths, [10, 40, 50])

    def test_fixed_and_pct(self):
        widths = calc_table(.10, 40, .50)
        self.assertEqual(widths, [10, 40, 50])

    def test_uneven_pct(self):
        widths = calc_table(1/3, 1/3, 1/3)
        self.assertEqual(widths, [33, 33, 33])

    def test_only_unspec_even(self):
        widths = calc_table(None, None, None, None)
        self.assertEqual(widths, [25, 25, 25, 25])

    def test_only_unspec_odd(self):
        widths = calc_table(None, None, None)
        self.assertEqual(widths, [33, 34, 33])

    def test_carry_over(self):
        widths = calc_table(1/3, 1/3, 1/3)
        self.assertEqual(widths, [33, 33, 33])

    def test_only_unspec_one(self):
        widths = calc_table(None)
        self.assertEqual(widths, [100])

    def test_only_unspec_two(self):
        widths = calc_table(None, None)
        self.assertEqual(widths, [50, 50])

    def test_mixed(self):
        widths = calc_table(25, .25, None, None)
        self.assertEqual(widths, [25, 25, 25, 25])

    def test_mixed_odd(self):
        widths = calc_table(19, 2/3, None, None, None, None, width=147)
        self.assertEqual(widths, [19, 98, 7, 8, 7, 8])


class TableRendering(unittest.TestCase):

    def table(self, *args, column_padding=0, **kwargs):
        self.get_lines, t = fileredir(L.Table, *args,
                                      column_padding=column_padding, **kwargs)
        return t

    def test_show_mode(self):
        t = self.table([10], width=10, clip=False, flex=False)
        text = 'A' * 20
        t.print_row([text])
        res = self.get_lines()[0]
        self.assertEqual(res, text)

    def test_clip_mode_no_cliptext(self):
        t = self.table([10], width=10, clip=True, cliptext='', flex=False)
        fits = 'A' * 10
        clipped = 'B' * 10
        t.print([[fits + clipped]])
        res = self.get_lines()[0]
        self.assertEqual(res, fits)

    def test_clip_mode_with_cliptext(self):
        for cliptext in ('*', '**', '***'):
            t = self.table([10], width=10, clip=True, cliptext=cliptext,
                           flex=False)
            fits = 'A' * (10 - len(cliptext))
            clipped = 'B' * 10
            t.print([[fits + clipped]])
            res = self.get_lines()[0]
            self.assertEqual(res, fits + cliptext)

    def test_flex_smoosh(self):
        t = self.table([None, None, None], width=12)
        text_a = ['1', '22', '333']
        text_b = ['333', '4444', '55555']
        t.print([text_a, text_b])
        first, second = self.get_lines()
        self.assertEqual(len(first.split()), 3)
        self.assertEqual(second, ''.join(text_b))
        self.assertEqual(len(second.split()), 1)
        t = self.table(column_padding=1, width=15)
        t.print([text_a, text_b])
        first, second = self.get_lines()
        self.assertEqual(second, '333 4444 55555 ')
        t = self.table(column_padding=2, width=18)
        t.print([text_a, text_b])
        first, second = self.get_lines()
        self.assertEqual(second, ' 333  4444  55555 ')
        t = self.table(column_padding=3, width=21)
        t.print([text_a, text_b])
        first, second = self.get_lines()
        self.assertEqual(second, ' 333   4444   55555  ')


class VTMLStringTests(unittest.TestCase):

    def test_vtstr_overclip_plain(self):
        startval = 'A' * 10
        s = L.vtmlrender(startval)
        self.assertEqual(s.clip(11), startval)
        self.assertEqual(s.clip(11).text(), startval)
        self.assertEqual(s.clip(20), startval)
        self.assertEqual(s.clip(20).text(), startval)

    def test_vtstr_noclip_plain(self):
        startval = 'A' * 10
        s = L.vtmlrender(startval)
        self.assertEqual(s.clip(10), startval)
        self.assertEqual(s.clip(10).text(), startval)

    def test_vtstr_underclip_plain(self):
        startval = 'A' * 10
        s = L.vtmlrender(startval)
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
        s = L.vtmlrender('<b>%s</b>' % startval)
        self.assertEqual(s.clip(11).text(), startval)
        self.assertEqual(s.clip(20).text(), startval)
        self.assertEqual(s.clip(11), s)
        self.assertEqual(s.clip(20), s)

    def test_vtstr_noclip_vtml(self):
        startval = 'A' * 10
        s = L.vtmlrender('<b>%s</b>' % startval)
        self.assertEqual(s.clip(10).text(), startval)
        self.assertEqual(s.clip(10), s)

    def test_vtstr_underclip_vtml(self):
        startval = 'A' * 10
        s = L.vtmlrender('<b>%s</b>' % startval)
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
        s = L.vtmlrender('<b>%s</b>' % 'AAAA')
        self.assertTrue(str(s.clip(2)).endswith('\033[0m'))

    def test_vtstr_overclip_with_cliptextt(self):
        startval = 'A' * 10
        s = L.vtmlrender(startval)
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
        s = L.vtmlrender(startval)
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
            self.assertEqual(L.vtmlrender(x), x)

    def test_ordering(self):
        self.assertGreater(L.vtmlrender('bbbb'), L.vtmlrender('aaaa'))
        self.assertLess(L.vtmlrender('aaaa'), L.vtmlrender('bbbb'))
        self.assertGreaterEqual(L.vtmlrender('bbbb'), L.vtmlrender('aaaa'))
        self.assertGreaterEqual(L.vtmlrender('aaaa'), L.vtmlrender('aaaa'))
        self.assertLessEqual(L.vtmlrender('aaaa'), L.vtmlrender('bbbb'))
        self.assertLessEqual(L.vtmlrender('aaaa'), L.vtmlrender('aaaa'))
        self.assertEqual(L.vtmlrender('aaaa'), L.vtmlrender('aaaa'))

    def test_add_same_type(self):
        a = L.vtmlrender('aaaa')
        b = L.vtmlrender('BBBB')
        ab = L.vtmlrender('aaaaBBBB')
        self.assertEqual(a+b, ab)
        self.assertEqual(str(a+b), str(ab))

    def test_iadd_same_type(self):
        a1 = L.vtmlrender('aaaa')
        a1 += L.vtmlrender('BBBB')
        a2 = L.vtmlrender('aaaaBBBB')
        self.assertEqual(a1, a2)

    def test_add_str_type(self):
        a = L.vtmlrender('aaaa')
        b = 'BBBB'
        ab = L.vtmlrender('aaaaBBBB')
        self.assertEqual(a+b, ab)
        self.assertEqual(str(a+b), str(ab))

    def test_iadd_str_type(self):
        a1 = L.vtmlrender('aaaa')
        a1 += 'BBBB'
        a2 = L.vtmlrender('aaaaBBBB')
        self.assertEqual(a1, a2)

    def test_iadd_unsupport_type(self):
        a1 = L.vtmlrender('foo')
        self.assertRaises(TypeError, lambda: a1 + 1)
        self.assertRaises(TypeError, lambda: a1 + b'bar')

    def test_amp_tail_single_char(self):
        """ Without a workaround this hits a bug in HTMLParser. """
        t = 'a&b'
        self.assertEqual(L.vtmlrender(t, strict=True), t)

    def test_amp_tail_double_char(self):
        t = 'a&bc'
        self.assertEqual(L.vtmlrender(t, strict=True), t)

    def test_amp_tail(self):
        t = 'a&'
        self.assertEqual(L.vtmlrender(t, strict=True), t)

    def test_amp_normal(self):
        for t in ('a&gt;', '&lt;', '&ltss;', '&;', '&abc;<other>'):
            self.assertEqual(L.vtmlrender(t, strict=True), t)

    def test_wrong_tag_tolerance(self):
        bad = ('foobar', 'foo', 'bar')
        perms = itertools.permutations(bad)
        for starts in perms:
            suffix = '<b>valid</b>'
            valid = str(L.vtmlrender(suffix, strict=True))
            self.assertIn('\033', valid, 'sanity test to validate next portion')
            ends = next(perms)  # makes for bad closes
            buf = ["<%s>asdf</%s>" % (x, y) for x, y in zip(starts, ends)]
            line = ''.join(buf)
            ugly = str(L.vtmlrender(line + suffix, strict=True))
            self.assertIn(valid, ugly)
            self.assertEqual(ugly, line + valid, 'partial conv did not work')

    def test_pound(self):
        for t in ('a#bc', 'a&#1;'):
            self.assertEqual(L.vtmlrender(t, strict=True), t)

class TableDataSupport(unittest.TestCase):

    def table(self, *args, **kwargs):
        return fileredir(L.Table, *args, **kwargs)

    def tabulate(self, *args, **kwargs):
        return fileredir(L.tabulate, *args, **kwargs)

    def test_columns_from_only_list_data(self):
        output, t = self.table()
        t.print([['one', 'two', 'three']])
        output, t = self.table()
        t.print([['one', 'two', 'three']] * 10)

    def test_columns_from_only_generator_data(self):
        output, t = self.table()
        def gen():
            yield ['one', 'two', 'three']
        t.print(gen())
        self.assertEqual(len(output()), 1)

        output, t = self.table()
        def gen():
            yield ['one', 'two', 'three']
            yield ['one', 'two', 'three']
        t.print(gen())
        self.assertEqual(len(output()), 2)

    def test_columns_from_headers(self):
        output, t = self.table(headers=['One', 'Two', 'Three'])
        t.print([['one', 'two', 'three']])

    def test_columns_from_accessors(self):
        output, t = self.table(accessors=['one', 'two', 'three'])
        t.print([{'one': 'ONE', 'two': 'TWO', 'three': 'THREE'}])

    def test_columns_from_none_is_error(self):
        output, t = self.table()
        self.assertRaises(L.RowsNotFound, t.make_renderer)

    def test_columns_width_spec_only(self):
        output, t = self.table(columns=[None, None, None])
        t.make_renderer()

    def test_columns_empty_style_spec(self):
        output, t = self.table(columns=[{}, {}, {}])
        t.make_renderer()

    def test_empty_iter(self):
        output, t = self.table([None])
        t.print(iter([]))
        self.assertFalse(output())

    def test_empty_list(self):
        output, t = self.table([None])
        t.print([])
        self.assertFalse(output())

    def test_zero_columns(self):
        output, t = self.table([])
        self.assertRaises(L.RowsNotFound, t.print, [])
        self.assertRaises(L.RowsNotFound, t.print, [[], []])
        self.assertRaises(L.RowsNotFound, t.print, [[], [], []])
        output, t = self.table([])
        self.assertRaises(L.RowsNotFound, t.print, [[], [], []])
        self.assertRaises(L.RowsNotFound, t.print, [[], []])
        self.assertRaises(L.RowsNotFound, t.print, [[]])
        self.assertRaises(L.RowsNotFound, t.print, [])

    def test_no_double_up_tabulate(self):
        output, t = self.tabulate([['abc']])
        self.assertEqual(''.join(output()).count('abc'), 1)
        output, t = self.tabulate([['abc'], ['XYZ']])
        val = ''.join(output())
        self.assertEqual(val.count('abc'), 1)
        self.assertEqual(val.count('XYZ'), 1)

    def test_dict_tabulate(self):
        output, t = self.tabulate([{
            "this_is_a_snake": "foo"
        }])
        self.assertEqual(t.headers[0], 'This Is A Snake')
        val = ''.join(output())
        self.assertIn('foo', val)
        self.assertEqual(val.count('foo'), 1)

    def test_tabulate_with_headers_empty(self):
        output, t = self.tabulate([], headers=['one'])
        self.assertIn('one', ''.join(output()))

    def test_tabulate_with_headers(self):
        output, t = self.tabulate([['ONE']], headers=['one'])
        self.assertIn('one', output()[0])
        self.assertIn(L.PlainTableRenderer.linebreak, output()[1])
        self.assertIn('ONE', output()[2])

    def test_empty_iter_tabulate(self):
        self.tabulate(iter([['header-only']]))

    def test_empty_iter_tabulate_headerarg(self):
        self.tabulate(iter([]), header=False)

    def test_empty_list_tabulate(self):
        self.tabulate([['header-only']])

    def test_empty_list_tabulate_headerarg(self):
        self.tabulate([], header=False)

    def test_empty_list_print(self):
        self.tabulate([], header=False)

    def test_generator_tabulate_headerless(self):
        def g():
            for x in range(2):
                yield [x]
        output, t = self.tabulate(g(), header=False)
        self.assertIn('1', ''.join(output()))

    def test_empty_add_footers_exc(self):
        t = L.Table()
        self.assertRaises(L.RowsNotFound, t.print_footer, 'foo')

    def test_add_footers_no_body(self):
        out, t = self.table(headers=['One'])
        t.print_footer('foo')
        self.assertIn('One', out()[0])
        self.assertIn('foo', out()[-1])

    def test_gen_seed_over_under(self):
        for seed_max in range(12):
            output, t = self.table([None], width=1, column_padding=0)
            t.max_seed = seed_max
            def stream():
                for i in range(10):
                    yield [i]
            t.print(stream())
            self.assertEqual([int(x) for x in output()], list(range(10)))

    def test_list_seed_over_under(self):
        for seed_max in range(12):
            output, t = self.table([None], width=1, column_padding=0)
            t.max_seed = seed_max
            data = [[i] for i in range(10)]
            t.print(data)
            self.assertEqual([int(x) for x in output()], list(range(10)))

    def test_empty_iter_noflex(self):
        output, t = self.table([None], flex=False)
        t.print(iter([]))
        self.assertFalse(output())

    def test_empty_list_noflex(self):
        output, t = self.table([20], flex=False)
        t.print([])
        self.assertFalse(output())

    def test_gen_seed_over_under_noflex(self):
        for seed_max in range(12):
            output, t = self.table([None], flex=False, width=1,
                                   column_padding=0)
            t.max_seed = seed_max
            def stream():
                for i in range(10):
                    yield [i]
            t.print(stream())
            self.assertEqual([int(x) for x in output()], list(range(10)))

    def test_list_seed_over_under_noflex(self):
        for seed_max in range(12):
            output, t = self.table([1], flex=False, width=1, column_padding=0)
            t.max_seed = seed_max
            data = [[i] for i in range(10)]
            t.print(data)
            self.assertEqual([int(x) for x in output()], list(range(10)))


class TableUsagePatterns(unittest.TestCase):

    def table(self, *args, column_padding=0, **kwargs):
        return fileredir(L.Table, *args, column_padding=column_padding, **kwargs)

    def test_headers_once(self):
        output, t = self.table(headers=['foo'], width=3)
        t.print([['one']])
        t.print([['two']])
        self.assertEqual(output(), ['foo', ('\u2014' * 3), 'one', 'two'])


class TableCalcs(unittest.TestCase):

    def test_unflex_spec_underflow(self):
        widths = calc_table(*[1/26] * 26)
        self.assertLess(statistics.variance(widths), 1)
        self.assertEqual(sum(widths), 78)  # uses floor() so it's lossy

    def test_unflex_unspec_underflow(self):
        widths = calc_table(*[None] * 26)
        self.assertLess(statistics.variance(widths), 1)
        self.assertEqual(sum(widths), 100)

    def test_equal_flex_underflow_all_fits(self):
        widths = calc_table(*[None] * 26, flex=True, data=[['a'] * 26])
        self.assertLess(statistics.variance(widths), 1)
        self.assertEqual(sum(widths), 100)

    def test_uniform_dist(self):
        dist = L.TableRenderer.uniform_dist
        for i in range(1, 101):
            for ii in range(151):
                d = dist(None, i, ii)
                self.assertEqual(sum(d), ii, (i, ii, d))


class TableArgGroup(unittest.TestCase):

    def test_table_group(self):
        L.Table.attach_arguments(argparse.ArgumentParser())


class TableClosingContext(unittest.TestCase):

    def test_Table_context_noaction(self):
        closed = False
        class TestTable(L.Table):
            def close(self, **kwargs):
                super().close(*kwargs)
                nonlocal closed
                closed = True
        with TestTable():
            pass
        self.assertTrue(closed)

    def test_Table_context_exc(self):
        class TestExc(Exception): pass
        class TestTable(L.Table):
            def close(this, exception=None):
                self.assertIs(exception[0], TestExc)
                super().close(exception)
        try:
            with TestTable():
                raise TestExc()
        except TestExc:
            pass


class JSONTableRenderer(unittest.TestCase):

    def setUp(self):
        t = L.Table([None], renderer='json')
        self.r = t.make_renderer([['']])

    def test_make_key_snakecase(self):
        self.assertEqual(self.r.make_key('snake_case'), 'snakeCase')
        self.assertEqual(self.r.make_key('snake_case_more'), 'snakeCaseMore')

    def test_make_key_snakecase_dblunderscore(self):
        self.assertEqual(self.r.make_key('snake__case'), 'snakeCase')

    def test_make_key_snakecase_leadunderscore(self):
        self.assertEqual(self.r.make_key('_snake_case'), 'SnakeCase')

    def test_make_key_snakecase_dblleadunderscore(self):
        self.assertEqual(self.r.make_key('__snake_case'), 'SnakeCase')

    def test_make_key_dupkeys(self):
        self.assertEqual(self.r.make_key('foo'), 'foo')
        self.assertEqual(self.r.make_key('foo'), 'foo1')
        self.assertEqual(self.r.make_key('foo'), 'foo2')
        self.assertEqual(self.r.make_key('foo2'), 'foo21')

    def test_make_key_scrub(self):
        self.assertEqual(self.r.make_key('!@#$%^&*()foo'), 'foo')
        self.assertEqual(self.r.make_key('!@#$%^&*()foo:"bar'), 'foobar')

    def test_make_key_space(self):
        self.assertEqual(self.r.make_key('This is some space - with-dashes'),
                         'thisIsSomeSpaceWithDashes')


class HTMLConversion(unittest.TestCase):

    a_format = '<blue><u>%s</u></blue>'

    def test_empty(self):
        L.htmlrender('')

    def test_parity(self):
        for tag in ('b', 'u'):
            markup = '<%s>stuff</%s>' % (tag, tag)
            self.assertEqual(L.html2vtml(markup), markup)

    def test_noop(self):
        self.assertEqual(L.html2vtml('<script>nope</script>'), '')

    def test_strip(self):
        self.assertEqual(L.html2vtml('<script>nope</script>'), '')
        self.assertEqual(L.html2vtml('before<script>nope</script>after'),
                         'beforeafter')

    def test_icase_tag(self):
        t = L.vtmlrender('<b>foo</b>')
        self.assertEqual(L.htmlrender('<B>foo</b>'), t)
        self.assertEqual(L.htmlrender('<B>foo</B>'), t)
        self.assertEqual(L.htmlrender('<b>foo</B>'), t)

    def test_a_tag_no_href(self):
        self.assertEqual(L.html2vtml('<a>foo</a>'), self.a_format % 'foo')

    def test_empty_href(self):
        self.assertEqual(L.html2vtml('<a href>foo</a>'), self.a_format % 'foo')

    def test_unquoted_href(self):
        self.assertEqual(L.html2vtml('<a href=link.here>foo</a>'),
                         self.a_format % 'foo (link.here)')

    def test_quoted_href(self):
        self.assertEqual(L.html2vtml('<a href="link.here">foo</a>'),
                         self.a_format % 'foo (link.here)')
        self.assertEqual(L.html2vtml("<a href='link.here'>foo</a>"),
                         self.a_format % 'foo (link.here)')

    def test_icase_href(self):
        for x in ('HREF', 'Href', 'hreF', 'href'):
            self.assertEqual(L.html2vtml('<a %s="link.here">foo</a>' % x),
                             self.a_format % 'foo (link.here)', x)
            self.assertEqual(L.html2vtml('<A %s="link.here">foo</a>' % x),
                             self.a_format % 'foo (link.here)')
            self.assertEqual(L.html2vtml('<A %s="link.here">foo</A>' % x),
                             self.a_format % 'foo (link.here)')
            self.assertEqual(L.html2vtml('<a %s="link.here">foo</A>' % x),
                             self.a_format % 'foo (link.here)')


class TreeData(unittest.TestCase):
    """ Tests to make sure tree doesn't blow up with various data inputs. """

    def setUp(self):
        self.stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

    def tearDown(self):
        sys.stdout.close()
        sys.stdout = self.stdout

    def test_treeprint_empty(self):
        self.assertRaises(TypeError, L.treeprint)

    def test_treeprint_dict(self):
        L.treeprint({})
        L.treeprint({1:1})
        L.treeprint({"1":1})
        L.treeprint({"1":"1"})
        L.treeprint({1:"1"})
        L.treeprint({"a":"1"})
        L.treeprint({"a":1})
        L.treeprint({"a": [1, 2]})
        L.treeprint({"a": ["1", 2]})
        L.treeprint({"a": ["1", "a"]})
        L.treeprint({"a": {}})
        L.treeprint({"a": {1:1}})

    def test_treeprint_cyclic(self):
        looper = {}
        looper['myself'] = looper
        self.assertRaises(ValueError, L.treeprint, looper)

    def test_treeprint_list(self):
        L.treeprint([])
        L.treeprint([1,2])
        L.treeprint(["a","b"])
        L.treeprint([{},"b"])
        L.treeprint([{1,2},"b"])
        L.treeprint([[]])
        L.treeprint([[1]])
        L.treeprint([1,[1]])
        L.treeprint([None])

    def test_treeprint_tuple(self):
        L.treeprint(())
        L.treeprint((1,2))
        L.treeprint(("a","b"))
        L.treeprint(({}, {}))

    def test_treeprint_numbers(self):
        L.treeprint(1)
        L.treeprint(0)

    def test_treeprint_odd(self):
        L.treeprint(None)
        L.treeprint(True)
        L.treeprint(False)
        L.treeprint(object())
        L.treeprint(object)
