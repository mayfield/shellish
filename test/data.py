
import unittest
from shellish.data import hone_cache, TTLCache

class TestTTLCache(unittest.TestCase):

    def ageless(self):
        """ Timer that never ages. """
        return 1

    def test_size_bounding(self):
        c = TTLCache(maxsize=1)
        self.assertEqual(len(c), 0)
        c[1] = 1
        self.assertEqual(c, {1:1})
        c[2] = 2
        self.assertEqual(c, {2:2})


class TestHoneCache(unittest.TestCase):

    def test_default_finder(self):
        misses = [0]
        @hone_cache()
        def test(prefix):
            return set(x for x in {'foo', 'foobar', 'baz'}
                       if x.startswith(prefix))
        self.assertEqual(test('f'), {'foo', 'foobar'})
        self.assertEqual(misses[0], 1)
        self.assertEqual(test('fo'), {'foo', 'foobar'})
        self.assertEqual(misses[0], 1)
        self.assertEqual(test('foob'), {'foobar'})
        self.assertEqual(misses[0], 1)
        self.assertEqual(test(''), {'foo', 'foobar', 'baz'})
        self.assertEqual(misses[0], 2)
        self.assertEqual(test('ba'), {'baz'})
        self.assertEqual(misses[0], 2)

    def test_path_finder(self):
        misses = [0]
        @hone_cache(refineby='container')
        def test(prefix):
            misses[0] += 1
            return [x for x in ('foo', 'foobar', 'baz')
                    if x.startswith(prefix)]
        self.assertEqual(test('f'), ['foo', 'foobar'])
        self.assertEqual(misses[0], 1)
        self.assertEqual(test('fo'), ['foo', 'foobar'])
        self.assertEqual(misses[0], 1)
        self.assertEqual(test('foob'), ['foobar'])
        self.assertEqual(misses[0], 1)
        self.assertEqual(test(''), ['foo', 'foobar', 'baz'])
        self.assertEqual(misses[0], 2)
        self.assertEqual(test('ba'), ['baz'])
        self.assertEqual(misses[0], 2)
