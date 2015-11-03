
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


class CommandCompose(unittest.TestCase):

    def test_naked(self):
        a = shellish.Command()
        self.assertRaises(SystemExit, a, argv='')

    def test_onlyrun(self):
        ok = object()
        a = shellish.Command(run=lambda _: ok)
        self.assertIs(a(argv=''), ok)

    def test_allrunners(self):
        refcnt = 0
        def runner(args, **ign):
            nonlocal refcnt
            refcnt += 1
        a = shellish.Command(prerun=runner, run=runner, postrun=runner)
        a(argv='')
        self.assertEqual(refcnt, 3)

    def test_subcommand_nameless(self):
        a = shellish.Command()
        b = shellish.Command()
        self.assertRaises(TypeError, a.add_subcommand, b)

    def test_subcommand_name_after_init(self):
        a = shellish.Command()
        b = shellish.Command()
        b.name = 'okay'
        a.add_subcommand(b)

    def test_subcommand_name_at_construct(self):
        a = shellish.Command()
        b = shellish.Command(name='okay')
        a.add_subcommand(b)
