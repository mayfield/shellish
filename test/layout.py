
import io
import unittest
from shellish import layout

class Tabular(unittest.TestCase):

    def test_only_pct(self):
        t = layout.Table([
            (.10, 'ten'),
            (.40, 'fourty'),
            (.50, 'fifty')
        ], 100)
        self.assertEquals(t.calc_widths(100), [10, 40, 50])

    def test_only_fixed(self):
        t = layout.Table([
            (10, 'ten'),
            (40, 'fourty'),
            (50, 'fifty')
        ], 100)
        self.assertEquals(t.calc_widths(100), [10, 40, 50])

    def test_fixed_and_pct(self):
        t = layout.Table([
            (.10, 'ten'),
            (40, 'fourty'),
            (.50, 'fifty')
        ], 100)
        self.assertEquals(t.calc_widths(100), [10, 40, 50])

    def test_uneven_pct(self):
        t = layout.Table([
            (1/3, 'ten'),
            (1/3, 'fourty'),
            (1/3, 'fifty')
        ], 100)
        self.assertEquals(t.calc_widths(100), [33, 33, 33])

    def test_only_unspec_even(self):
        t = layout.Table([
            (None, 'one'),
            (None, 'two'),
            (None, 'three'),
            (None, 'four')
        ], 100)
        self.assertEquals(t.calc_widths(100), [25, 25, 25, 25])

    def test_only_unspec_odd(self):
        t = layout.Table([
            (None, 'one'),
            (None, 'two'),
            (None, 'three'),
        ], 100)
        self.assertEquals(t.calc_widths(100), [33, 33, 33])

    def test_only_unspec_one(self):
        t = layout.Table([
            (None, 'one'),
        ], 100)
        self.assertEquals(t.calc_widths(100), [100])

    def test_only_unspec_two(self):
        t = layout.Table([
            (None, 'one'),
            (None, 'two'),
        ], 100)
        self.assertEquals(t.calc_widths(100), [50, 50])

    def test_mixed(self):
        t = layout.Table([
            (25, 'one'),
            (.25, 'two'),
            (None, 'three'),
            (None, 'four'),
        ], 100)
        self.assertEquals(t.calc_widths(100), [25, 25, 25, 25])

    def test_mixed_odd(self):
        t = layout.Table([
            (19, 'one'),
            (2/3, 'two'),
            (None, 'three'),
            (None, 'four'),
            (None, 'five'),
            (None, 'six'),
        ], 147)
        self.assertEquals(t.calc_widths(147), [19, 98, 7, 7, 7, 7])


class TableRendering(unittest.TestCase):

    def setUp(self):
        self.output = io.StringIO()
        super().setUp()

    def get_output(self):
        return self.output.getvalue().splitlines()

    def test_show_mode(self):
        t = layout.Table([
            (10, 'one'),
        ], 10, clip=False, file=self.output)
        t.render([['A' * 12]])
        res = self.get_output()[1]
        print(res)
        print(res)

    def test_clip_mode(self):
        t = layout.Table([
            (10, 'one'),
        ], 10, clip=True, file=self.output)
        t.render([['A ' * 12]])
        res = self.get_output()[1]
        print(res)
        print(res)

    def test_only_flex(self):
        t = layout.Table([
            (None, 'one'),
            (None, 'one'),
            (None, 'one'),
        ], 40, file=self.output, flex=True)
        t.render([['1', '22', '333'], ['333', '4444', '55555']])
        res = self.get_output()[1]
        print(res)
