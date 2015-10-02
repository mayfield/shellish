"""
Sanity tests for the shellish library.
"""

import shellish
import unittest


class ShellSanity(unittest.TestCase):

    def test_shell_init(self):
        self.assertRaises(TypeError, shellish.Shell)
        shellish.Shell(shellish.Command())


class CommandSanity(unittest.TestCase):

    def test_command_init(self):
        class Foo(shellish.Command):
            """ foo """
            pass
        Foo()
        shellish.Command()

    def test_no_title_desc_by_subclass(self):
        class Foo(shellish.Command):
            pass
        f = Foo()
        self.assertEqual(f.title, None)
        self.assertEqual(f.desc, None)

    def test_no_title_desc_by_compose(self):
        f = shellish.Command()
        self.assertEqual(f.title, None)
        self.assertEqual(f.desc, None)

    def test_title_desc_by_subclass_attrs(self):
        class Foo(shellish.Command):
            title = 'foo'
            desc = 'bar'
        f = Foo()
        self.assertEqual(f.title, 'foo')
        self.assertEqual(f.desc, 'bar')

    def test_title_desc_by_subclass_docstring_2line_padded(self):
        class Foo(shellish.Command):
            """ foo 
            bar """
        f = Foo()
        self.assertEqual(f.title, 'foo')
        self.assertEqual(f.desc, 'bar')

    def test_title_desc_by_subclass_docstring_2line_unpadded(self):
        class Foo(shellish.Command):
            """foo
            bar"""
        f = Foo()
        self.assertEqual(f.title, 'foo')
        self.assertEqual(f.desc, 'bar')

    def test_title_desc_by_subclass_docstring_3line_padded_gap(self):
        class Foo(shellish.Command):
            """ foo 

            bar """
        f = Foo()
        self.assertEqual(f.title, 'foo')
        self.assertEqual(f.desc, 'bar')

    def test_title_desc_by_subclass_docstring_3line_extrahead(self):
        class Foo(shellish.Command):
            """
            foo
            bar """
        f = Foo()
        self.assertEqual(f.title, 'foo')
        self.assertEqual(f.desc, 'bar')

    def test_title_desc_by_subclass_docstring_3line_extrafoot(self):
        class Foo(shellish.Command):
            """foo
            bar
            """
        f = Foo()
        self.assertEqual(f.title, 'foo')
        self.assertEqual(f.desc, 'bar')

    def test_title_desc_by_subclass_docstring_4line(self):
        class Foo(shellish.Command):
            """
            foo
            bar
            """
        f = Foo()
        self.assertEqual(f.title, 'foo')
        self.assertEqual(f.desc, 'bar')

    def test_empty_docstring(self):
        class Foo(shellish.Command):
            """"""
        f = Foo()
        self.assertEqual(f.title, None)
        self.assertEqual(f.desc, None)

        class Foo(shellish.Command):
            """ """
        f = Foo()
        self.assertEqual(f.title, None)
        self.assertEqual(f.desc, None)

        class Foo(shellish.Command):
            """
            """
        f = Foo()
        self.assertEqual(f.title, None)
        self.assertEqual(f.desc, None)

        class Foo(shellish.Command):
            """

            """
        f = Foo()
        self.assertEqual(f.title, None)
        self.assertEqual(f.desc, None)
