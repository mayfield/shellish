"""
Sanity tests for the traceback formatting
"""

import io
import shellish
import unittest


class TracebackSanity(unittest.TestCase):

    def assertTracebackFormat(self, traceback_lines, exc_name):
        """ Rougly assert that a list of traceback lines looks okay. """
        self.assertTrue(traceback_lines)
        self.assertIn('1.', traceback_lines[0])
        self.assertIn('File', traceback_lines[0])
        self.assertIn('line', traceback_lines[0])
        self.assertIn(exc_name, traceback_lines[-1])

    def test_format(self):
        try:
            raise ValueError('foo')
        except ValueError as e:
            self.assertTracebackFormat(list(shellish.format_exception(e)),
                                       'ValueError')

    def test_format_with_cause(self):
        try:
            raise ValueError('foo')
        except ValueError as outer:
            try:
                raise TypeError('bar')
            except TypeError as inner:
                self.assertTracebackFormat(list(shellish.format_exception(inner)),
                                           'TypeError')

    def test_print(self):
        buf = io.StringIO()
        try:
            raise ValueError('foo')
        except ValueError as e:
            shellish.print_exception(e, file=buf)
            self.assertTrue(buf.getvalue())
