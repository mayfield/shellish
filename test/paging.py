import shellish
import unittest
import io
import sys
import tempfile


class TTYPagingTests(unittest.TestCase):

    def test_small(self):
        with tempfile.TemporaryDirectory() as tdir:
            outfile = '%s/out' % tdir
            with shellish.pager_redirect('test', pagercmd='head -n1 > %s' %
                                         outfile):
                for x in range(10):
                    print(x)
            with open(outfile) as f:
                self.assertEqual(f.read(), '0\n')

    def test_pipe_overflow(self):
        with tempfile.TemporaryDirectory() as tdir:
            outfile = '%s/out' % tdir
            with shellish.pager_redirect('test', pagercmd='head -n1 > %s' %
                                         outfile):
                for x in range(10000):
                    print(('%d' % x) * 1000)
            with open(outfile) as f:
                self.assertEqual(f.read().rstrip(), '0' * 1000)

    def test_nested(self):
        with tempfile.TemporaryDirectory() as tdir:
            outfile1 = '%s/out1' % tdir
            outfile2 = '%s/out2' % tdir
            with shellish.pager_redirect('test', pagercmd='cat > %s' %
                                         outfile1):
                print('outer')
                with shellish.pager_redirect('test', pagercmd='cat > %s' %
                                             outfile2):
                    print('inner')
            self.assertRaises(IOError, open, outfile2)
            with open(outfile1) as f:
                self.assertEqual(list(f), ['outer\n', 'inner\n'])
