
import shellish
import unittest


class TestNesting(unittest.TestCase):

    def test_nest1_by_class(self):
        class A(shellish.Command):
            name = 'a'
            def run(self, args):
                return 'A'

        class B(shellish.Command):
            name = 'b'
            def run(self, args):
                return 'B'

        class B2(shellish.Command):
            name = 'b2'
            def run(self, args):
                return 'B2'

        a = A()
        a.add_subcommand(B)
        a.add_subcommand(B2())
        self.assertEqual(a(argv=''), 'A')
        self.assertEqual(a(argv='b'), 'B')
        self.assertEqual(a(argv='b2'), 'B2')

    def test_default_subcommand(self):
        class A(shellish.Command):
            name = 'a'
            def run(self, args):
                return 'A'

        class B(shellish.Command):
            name = 'b'
            def run(self, args):
                return 'B'

        a = A()
        a.add_subcommand(B, default=True)
        self.assertEqual(a(argv=''), 'B')
        self.assertEqual(a(argv='b'), 'B')
