
import unittest
from shellish.data import hone_cache, ttl_cache, TTLMapping


class TestTTLMapping(unittest.TestCase):

    def ageless(self):
        """ Timer that never ages. """
        return 1

    def test_contains_nottl_max(self):
        c = TTLMapping(maxsize=2)
        c[1] = 11
        self.assertIn(1, c)
        c[2] = 22
        self.assertIn(2, c)
        self.assertIn(1, c)
        c[3] = 33
        self.assertIn(3, c)
        self.assertIn(2, c)
        self.assertNotIn(1, c)

    def test_contains_nottl_nomax(self):
        c = TTLMapping()
        c[1] = 11
        self.assertIn(1, c)
        c[2] = 22
        self.assertIn(2, c)
        self.assertIn(1, c)

    def test_contains_ttl_nomax(self):
        timeval = 1
        timer = lambda: timeval
        c = TTLMapping(ttl=2, timer=timer)
        c[1] = 11
        self.assertIn(1, c)
        timeval = 2
        c[2] = 22
        self.assertIn(2, c)
        self.assertIn(1, c)
        timeval = 3
        self.assertIn(2, c)
        self.assertIn(1, c)
        timeval = 4
        self.assertIn(2, c)
        self.assertNotIn(1, c)

    def test_contains_ttl_max(self):
        timeval = 1
        timer = lambda: timeval
        c = TTLMapping(ttl=2, maxsize=2, timer=timer)
        c[1] = 11
        self.assertIn(1, c)
        timeval = 2
        c[2] = 22
        self.assertIn(2, c)
        self.assertIn(1, c)
        timeval = 3
        self.assertIn(2, c)
        self.assertIn(1, c)
        timeval = 4
        self.assertIn(2, c)
        self.assertNotIn(1, c)
        c[3] = 33
        self.assertIn(2, c)
        self.assertIn(3, c)
        timeval = 5
        self.assertIn(3, c)
        self.assertNotIn(2, c)
        timeval = 7
        self.assertNotIn(3, c)
        self.assertNotIn(2, c)

    def test_size_nottl_bounding(self):
        c = TTLMapping(maxsize=1)
        self.assertEqual(len(c), 0)
        self.assertEqual(c, {})
        c[1] = 11
        self.assertEqual(len(c), 1)
        self.assertEqual(c, {1: 11})
        c[2] = 22
        self.assertEqual(len(c), 1)
        self.assertEqual(c, {2: 22})

    def test_size_ttl_bounding(self):
        for maxsize in (None, 5):
            timeval = 1
            timer = lambda: timeval
            c = TTLMapping(ttl=1, timer=timer, maxsize=maxsize)
            self.assertEqual(len(c), 0)
            self.assertEqual(c, {})
            c[1] = 1
            self.assertEqual(len(c), 1)
            self.assertEqual(c, {1: 1})
            timeval = 3
            self.assertEqual(len(c), 0)
            self.assertEqual(c, {})

    def test_iteration(self):
        for maxsize in (None, 5):
            timeval = 1
            timer = lambda: timeval
            c = TTLMapping(ttl=1, timer=timer, maxsize=128)
            c.update({1: 11, 2: 22})
            keys = list(c)
            self.assertEqual(list(keys), [1, 2])
            fast = iter(c)
            self.assertEqual(list(fast), [1, 2])
            slow = iter(c)
            timeval = 3
            self.assertEqual(list(slow), [])
            c[1] = 11
            c[2] = 22
            medium = iter(c)
            first = next(medium)
            self.assertEqual(first, 1)
            timeval = 5
            self.assertRaises(StopIteration, lambda: next(medium))


class TestTTLCache(unittest.TestCase):

    def test_pos_args(self):
        i = 0

        @ttl_cache(None)
        def test(a, b, c):
            nonlocal i
            i += 1
            return i
        self.assertEqual(test(1, 2, 3), 1)
        self.assertEqual(test(1, 2, 3), 1)
        self.assertEqual(test(1, 2, 3), 1)
        self.assertEqual(test.cache_info().hits, 2)
        self.assertEqual(test(1, 2, 4), 2)
        self.assertEqual(test.cache_info().misses, 2)


class TestHoneCache(unittest.TestCase):

    def test_default_finder(self):

        @hone_cache()
        def test(prefix):
            return set(x for x in {'foo', 'foobar', 'baz'}
                       if x.startswith(prefix))
        self.assertEqual(test('f'), {'foo', 'foobar'})
        self.assertEqual(test.cache_info().misses, 1)
        self.assertEqual(test('fo'), {'foo', 'foobar'})
        self.assertEqual(test.cache_info().misses, 1)
        self.assertEqual(test('foob'), {'foobar'})
        self.assertEqual(test.cache_info().misses, 1)
        self.assertEqual(test(''), {'foo', 'foobar', 'baz'})
        self.assertEqual(test.cache_info().misses, 2)
        self.assertEqual(test('ba'), {'baz'})
        self.assertEqual(test.cache_info().misses, 2)

    def test_tito(self):
        """ Type In Type Out """
        for xtype in list, set, tuple, frozenset:

            @hone_cache()
            def test(prefix):
                return xtype(x for x in ('foo', 'foobar', 'baz')
                             if x.startswith(prefix))
            self.assertEqual(test('f'), xtype(('foo', 'foobar')))
            self.assertEqual(test.cache_info().misses, 1)
            self.assertEqual(test('fo'), xtype(('foo', 'foobar')))
            self.assertEqual(test.cache_info().misses, 1)
            self.assertEqual(test('foob'), xtype(('foobar',)))
            self.assertEqual(test.cache_info().misses, 1)
            self.assertEqual(test(''), xtype(('foo', 'foobar', 'baz')))
            self.assertEqual(test.cache_info().misses, 2)
            self.assertEqual(test('ba'), xtype(('baz',)))
            self.assertEqual(test.cache_info().misses, 2)

    def test_path_finder_simple(self):
        tree = {
            "level1": {
                "level2": {
                    "leaf": 123
                }
            }
        }

        @hone_cache(refineby='container')
        def test(path):
            offt = tree
            for x in path:
                offt = offt[x]
            return offt
        self.assertEqual(test(('level1',)), tree['level1'])
        self.assertEqual(test.cache_info().misses, 1)
        self.assertEqual(test(('level1',)), tree['level1'])
        self.assertEqual(test.cache_info().hits, 1)
        self.assertEqual(test(('level1', 'level2')), tree['level1']['level2'])
        self.assertEqual(test.cache_info().partials, 1)

    def test_path_finder_mixed_type(self):
        tree = {
            "level1": [{
                "level2": {
                    "leaf": 123
                }
            }]
        }

        @hone_cache(refineby='container')
        def test(path):
            offt = tree
            for x in path:
                offt = offt[x]
            return offt
        self.assertEqual(test(('level1',)), tree['level1'])
        self.assertEqual(test.cache_info().misses, 1)
        self.assertEqual(test(('level1',)), tree['level1'])
        self.assertEqual(test.cache_info().hits, 1)
        self.assertEqual(test(('level1', 0, 'level2')),
                         tree['level1'][0]['level2'])
        self.assertEqual(test.cache_info().partials, 1)
