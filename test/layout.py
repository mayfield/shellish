
import argparse
import io
import statistics
import unittest
from shellish.layout import Table, TableRenderer, vtmlrender, tabulate, \
                            RowsNotFound


def calc_table(*columns, width=100, data=None, flex=False):
    t = Table(columns=columns, width=width, flex=flex, column_padding=0)
    return t.make_renderer(data or []).widths


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
        self.output = io.StringIO()
        return Table(*args, file=self.output, column_padding=column_padding,
                     **kwargs)

    def get_lines(self):
        return self.output.getvalue().splitlines()

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
        s = vtmlrender(startval)
        self.assertEqual(s.clip(11), startval)
        self.assertEqual(s.clip(11).text(), startval)
        self.assertEqual(s.clip(20), startval)
        self.assertEqual(s.clip(20).text(), startval)

    def test_vtstr_noclip_plain(self):
        startval = 'A' * 10
        s = vtmlrender(startval)
        self.assertEqual(s.clip(10), startval)
        self.assertEqual(s.clip(10).text(), startval)

    def test_vtstr_underclip_plain(self):
        startval = 'A' * 10
        s = vtmlrender(startval)
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
        s = vtmlrender('<b>%s</b>' % startval)
        self.assertEqual(s.clip(11).text(), startval)
        self.assertEqual(s.clip(20).text(), startval)
        self.assertEqual(s.clip(11), s)
        self.assertEqual(s.clip(20), s)

    def test_vtstr_noclip_vtml(self):
        startval = 'A' * 10
        s = vtmlrender('<b>%s</b>' % startval)
        self.assertEqual(s.clip(10).text(), startval)
        self.assertEqual(s.clip(10), s)

    def test_vtstr_underclip_vtml(self):
        startval = 'A' * 10
        s = vtmlrender('<b>%s</b>' % startval)
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
        s = vtmlrender('<b>%s</b>' % 'AAAA')
        self.assertTrue(str(s.clip(2)).endswith('\033[0m'))

    def test_vtstr_overclip_with_cliptextt(self):
        startval = 'A' * 10
        s = vtmlrender(startval)
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
        s = vtmlrender(startval)
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
            '<nope>asdf',
            '<b>asdf</notit>',
        ]
        for x in bad:
            self.assertEqual(vtmlrender(x), x)

    def test_ordering(self):
        self.assertGreater(vtmlrender('bbbb'), vtmlrender('aaaa'))
        self.assertLess(vtmlrender('aaaa'), vtmlrender('bbbb'))
        self.assertGreaterEqual(vtmlrender('bbbb'), vtmlrender('aaaa'))
        self.assertGreaterEqual(vtmlrender('aaaa'), vtmlrender('aaaa'))
        self.assertLessEqual(vtmlrender('aaaa'), vtmlrender('bbbb'))
        self.assertLessEqual(vtmlrender('aaaa'), vtmlrender('aaaa'))
        self.assertEqual(vtmlrender('aaaa'), vtmlrender('aaaa'))

    def test_add_same_type(self):
        a = vtmlrender('aaaa')
        b = vtmlrender('BBBB')
        ab = vtmlrender('aaaaBBBB')
        self.assertEqual(a+b, ab)
        self.assertEqual(str(a+b), str(ab))

    def test_iadd_same_type(self):
        a1 = vtmlrender('aaaa')
        a1 += vtmlrender('BBBB')
        a2 = vtmlrender('aaaaBBBB')
        self.assertEqual(a1, a2)

    def test_add_str_type(self):
        a = vtmlrender('aaaa')
        b = 'BBBB'
        ab = vtmlrender('aaaaBBBB')
        self.assertEqual(a+b, ab)
        self.assertEqual(str(a+b), str(ab))

    def test_iadd_str_type(self):
        a1 = vtmlrender('aaaa')
        a1 += 'BBBB'
        a2 = vtmlrender('aaaaBBBB')
        self.assertEqual(a1, a2)

    def test_iadd_unsupport_type(self):
        a1 = vtmlrender('foo')
        self.assertRaises(TypeError, lambda: a1 + 1)
        self.assertRaises(TypeError, lambda: a1 + b'bar')


class TableDataSupport(unittest.TestCase):

    def table(self, *args, **kwargs):
        file = io.StringIO()
        output = lambda: file.getvalue().splitlines()
        return output, Table(*args, file=file, **kwargs)

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
        self.assertRaises(RowsNotFound, t.make_renderer)

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
        self.assertRaises(RowsNotFound, t.print, [])
        self.assertRaises(RowsNotFound, t.print, [[], []])
        self.assertRaises(RowsNotFound, t.print, [[], [], []])
        output, t = self.table([])
        self.assertRaises(RowsNotFound, t.print, [[], [], []])
        self.assertRaises(RowsNotFound, t.print, [[], []])
        self.assertRaises(RowsNotFound, t.print, [[]])
        self.assertRaises(RowsNotFound, t.print, [])

    def test_dict_tabulate(self):
        out = io.StringIO()
        t = tabulate([{
            "this_is_a_snake": "foo"
        }], file=out)
        self.assertEqual(t.headers[0], 'This Is A Snake')
        self.assertIn('foo', out.getvalue())

    def test_tabulate_with_headers_empty(self):
        out = io.StringIO()
        tabulate([], headers=['one'], file=out)
        self.assertIn('one', out.getvalue())

    def test_tabulate_with_headers(self):
        out = io.StringIO()
        tabulate([['ONE']], headers=['one'], file=out)
        self.assertIn('one', out.getvalue())
        self.assertIn('ONE', out.getvalue())

    def test_empty_iter_tabulate(self):
        tabulate(iter([['header-only']]))

    def test_empty_iter_tabulate_headerarg(self):
        tabulate(iter([]), header=False)

    def test_empty_list_tabulate(self):
        tabulate([['header-only']])

    def test_empty_list_tabulate_headerarg(self):
        tabulate([], header=False)

    def test_empty_list_print(self):
        tabulate([], header=False)

    def test_generator_tabulate_headerless(self):
        def g():
            for x in range(2):
                yield [x]
        out = io.StringIO()
        tabulate(g(), header=False, file=out)
        self.assertIn('1', out.getvalue())

    def test_empty_add_footers_exc(self):
        t = Table()
        self.assertRaises(RowsNotFound, t.print_footer, 'foo')

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
        self.output = io.StringIO()
        return Table(*args, file=self.output, column_padding=column_padding,
                     **kwargs)

    def get_lines(self):
        return self.output.getvalue().splitlines()

    def test_headers_once(self):
        t = self.table(headers=['foo'], width=3)
        t.print([['one']])
        t.print([['two']])
        self.assertEqual(self.get_lines(), ['foo', ('\u2014' * 3), 'one',
                                            'two'])


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
        dist = TableRenderer.uniform_dist
        for i in range(1, 101):
            for ii in range(151):
                d = dist(None, i, ii)
                self.assertEqual(sum(d), ii, (i, ii, d))


class TableArgGroup(unittest.TestCase):

    def test_table_group(self):
        Table.add_format_group(argparse.ArgumentParser())


class TableClosingContext(unittest.TestCase):

    def test_Table_context_noaction(self):
        closed = False
        class TestTable(Table):
            def close(self, **kwargs):
                super().close(*kwargs)
                nonlocal closed
                closed = True
        with TestTable():
            pass
        self.assertTrue(closed)

    def test_Table_context_exc(self):
        class TestExc(Exception): pass
        class TestTable(Table):
            def close(this, exception=None):
                self.assertIs(exception[0], TestExc)
                super().close(exception)
        try:
            with TestTable():
                raise TestExc()
        except TestExc:
            pass
