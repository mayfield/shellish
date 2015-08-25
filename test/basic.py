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

    def test_docstring_required(self):
        class Foo(shellish.Command):
            pass
        self.assertRaises(SyntaxError, Foo)
