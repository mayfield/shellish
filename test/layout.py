
import io
import unittest
from shellish.layout import Table, tabulate

class TabularUnflex(unittest.TestCase):

    def calc_table(self, *column_spec, width=100, flex=False, pad=0):
        t = Table(column_spec=column_spec, width=width, flex=flex,
                  column_pad=0)
        t.render([])
        return t.render_spec['calculated_widths']

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

    def render_table(self, *args, column_pad=0, **kwargs):
        self.output = io.StringIO()
        return Table(*args, file=self.output, column_pad=column_pad, **kwargs)

    def get_lines(self):
        return self.output.getvalue().splitlines()

    def test_show_mode(self):
        t = self.render_table([10], width=10, clip=False, flex=False)
        text = 'A' * 20
        t.write_row([text])
        res = self.get_lines()[0]
        self.assertEqual(res, text)

    def test_clip_mode_no_cliptext(self):
        t = self.render_table([10], width=10, clip=True, cliptext='',
                              cliptext_format='%s', flex=False)
        fits = 'A' * 10
        clipped = 'B' * 10
        t.render([[fits + clipped]])
        res = self.get_lines()[0]
        self.assertEqual(res, fits)

    def test_clip_mode_with_cliptext(self):
        for cliptext in ('*', '**', '***'):
            t = self.render_table([10], width=10, clip=True, cliptext=cliptext,
                                  cliptext_format='%s', flex=False)
            fits = 'A' * (10 - len(cliptext))
            clipped = 'B' * 10
            t.render([[fits + clipped]])
            res = self.get_lines()[0]
            self.assertEqual(res, fits + cliptext)

    def test_flex_smoosh(self):
        t = self.render_table([None, None, None], width=40)
        text_a = ['1', '22', '333']
        text_b = ['333', '4444', '55555']
        t.write([text_a, text_b])
        first, second = self.get_lines()
        self.assertEqual(len(first.split()), 3)
        self.assertEqual(len(second.split()), 1)
        for i in range(1, 3):
            t = self.render_table([None, None, None], column_pad=i, width=40)
            t.write([text_a, text_b])
            first, second = self.get_lines()
            self.assertEqual(second, (' ' * i).join(text_b) + (' ' * i))
