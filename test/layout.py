
import io
import unittest
from shellish.layout import Table, vtmlrender, tabulate

class TabularUnflex(unittest.TestCase):

    def calc_table(self, *columns, width=100):
        t = Table(columns=columns, width=width, flex=False, column_padding=0)
        return t.render([]).widths

    def test_only_pct(self):
        widths = self.calc_table(.10, .40, .50)
        self.assertEqual(widths, [10, 40, 50])

    def test_only_fixed(self):
        widths = self.calc_table(10, 40, 50)
        self.assertEqual(widths, [10, 40, 50])

    def test_fixed_and_pct(self):
        widths = self.calc_table(.10, 40, .50)
        self.assertEqual(widths, [10, 40, 50])

    def test_uneven_pct(self):
        widths = self.calc_table(1/3, 1/3, 1/3)
        self.assertEqual(widths, [33, 33, 33])

    def test_only_unspec_even(self):
        widths = self.calc_table(None, None, None, None)
        self.assertEqual(widths, [25, 25, 25, 25])

    def test_only_unspec_odd(self):
        widths = self.calc_table(None, None, None)
        self.assertEqual(widths, [33, 33, 33])

    def test_only_unspec_one(self):
        widths = self.calc_table(None)
        self.assertEqual(widths, [100])

    def test_only_unspec_two(self):
        widths = self.calc_table(None, None)
        self.assertEqual(widths, [50, 50])

    def test_mixed(self):
        widths = self.calc_table(25, .25, None, None)
        self.assertEqual(widths, [25, 25, 25, 25])

    def test_mixed_odd(self):
        widths = self.calc_table(19, 2/3, None, None, None, None, width=147)
        self.assertEqual(widths, [19, 98, 7, 7, 7, 7])


class TableRendering(unittest.TestCase):

    def render_table(self, *args, column_padding=0, **kwargs):
        self.output = io.StringIO()
        return Table(*args, file=self.output, column_padding=column_padding,
                     **kwargs)

    def get_lines(self):
        return self.output.getvalue().splitlines()

    def test_show_mode(self):
        t = self.render_table([10], width=10, clip=False, flex=False)
        text = 'A' * 20
        t.print_row([text])
        res = self.get_lines()[0]
        self.assertEqual(res, text)

    def test_clip_mode_no_cliptext(self):
        t = self.render_table([10], width=10, clip=True, cliptext='',
                              flex=False)
        fits = 'A' * 10
        clipped = 'B' * 10
        t.print([[fits + clipped]])
        res = self.get_lines()[0]
        self.assertEqual(res, fits)

    def test_clip_mode_with_cliptext(self):
        for cliptext in ('*', '**', '***'):
            t = self.render_table([10], width=10, clip=True, cliptext=cliptext,
                                  flex=False)
            fits = 'A' * (10 - len(cliptext))
            clipped = 'B' * 10
            t.print([[fits + clipped]])
            res = self.get_lines()[0]
            self.assertEqual(res, fits + cliptext)

    def test_flex_smoosh(self):
        t = self.render_table([None, None, None], width=12)
        text_a = ['1', '22', '333']
        text_b = ['333', '4444', '55555']
        t.print([text_a, text_b])
        first, second = self.get_lines()
        self.assertEqual(len(first.split()), 3)
        self.assertEqual(second, ''.join(text_b))
        self.assertEqual(len(second.split()), 1)
        t = self.render_table(column_padding=1, width=15)
        t.print([text_a, text_b])
        first, second = self.get_lines()
        self.assertEqual(second, '333 4444 55555 ')
        t = self.render_table(column_padding=2, width=18)
        t.print([text_a, text_b])
        first, second = self.get_lines()
        self.assertEqual(second, ' 333  4444  55555 ')
        t = self.render_table(column_padding=3, width=21)
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
        self.assertRaises(ValueError, t.render)

    def test_columns_width_spec_only(self):
        output, t = self.table(columns=[None, None, None])
        t.render()

    def test_columns_empty_style_spec(self):
        output, t = self.table(columns=[{}, {}, {}])
        t.render()
