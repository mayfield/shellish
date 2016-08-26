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
        self.assertIn('Traceback (most recent call last)', traceback_lines[0])
        self.assertIn('File', traceback_lines[1])
        self.assertIn('line', traceback_lines[1])
        self.assertIn('1.', traceback_lines[-3])
        self.assertIn('File', traceback_lines[-3])
        self.assertIn('line', traceback_lines[-3])
        self.assertIn(exc_name, traceback_lines[-1])

    def stack_push(self, levels, callback, *args, **kwargs):
        if levels:
            return self.stack_push(levels - 1, callback, *args, **kwargs)
        else:
            return callback(*args, **kwargs)

    def test_format_single(self):
        def raiser():
            raise ValueError('foo')
        try:
            self.stack_push(10, raiser)
        except ValueError as e:
            self.assertTracebackFormat(list(shellish.format_exception(e)),
                                       'ValueError')

    def test_format_1stack(self):
        def raiser():
            raise ValueError('foo')
        try:
            self.stack_push(1, raiser)
        except ValueError as e:
            self.assertTracebackFormat(list(shellish.format_exception(e)),
                                       'ValueError')

    def test_format_10stack(self):
        def raiser():
            raise ValueError('foo')
        try:
            self.stack_push(10, raiser)
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
