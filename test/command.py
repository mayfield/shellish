
import os
import shellish
import sys
import tempfile
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
        a = shellish.Command(name='a')
        self.assertRaises(SystemExit, a, argv='')

    def test_onlyrun(self):
        ok = object()
        a = shellish.Command(name='a', run=lambda _: ok)
        self.assertIs(a(argv=''), ok)

    def test_allrunners(self):
        refcnt = 0
        def runner(args, **ign):
            nonlocal refcnt
            refcnt += 1
        a = shellish.Command(name='a', prerun=runner, run=runner,
                             postrun=runner)
        a(argv='')
        self.assertEqual(refcnt, 3)

    def test_command_nameless(self):
        self.assertRaises(RuntimeError, shellish.Command)

    def test_subcommand_name_at_construct(self):
        a = shellish.Command(name='a')
        b = shellish.Command(name='b')
        a.add_subcommand(b)


class CommandFileArguments(unittest.TestCase):

    def setUp(self):
        self._cwd_save = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self._cwd_save)
        self.tmp.cleanup()

    def test_file_argument_defaults_not_found(self):
        def run(args):
            self.assertRaises(FileNotFoundError, args.foo().__enter__)
        cmd = shellish.Command(name='test', run=run)
        cmd.add_file_argument('--foo')
        cmd(argv='--foo doesnotexist')

    def test_file_argument_defaults_stdio(self):
        flushed = False
        class Stdin(object):
            def flush(self):
                nonlocal flushed
                flushed = True
        stdin_setinel = Stdin()
        def run(args):
            with args.foo as f:
                self.assertIs(f, stdin_setinel)
                self.assertFalse(flushed)
            self.assertTrue(flushed)
        cmd = shellish.Command(name='test', run=run)
        cmd.add_file_argument('--foo')
        stdin = sys.stdin
        sys.stdin = stdin_setinel
        try:
            cmd(argv='--foo -')
        finally:
            sys.stdin = stdin

    def test_file_argument_stdout(self):
        def run(args):
            with args.foo as f:
                self.assertIs(f, sys.stdout)
        cmd = shellish.Command(name='test', run=run)
        cmd.add_file_argument('--foo', mode='w')
        cmd(argv='--foo -')

    def test_file_argument_read_found(self):
        def run(args):
            with args.foo as f:
                self.assertTrue(f.name.endswith('exists'))
                self.assertTrue(f.mode, 'r')
        open('exists', 'w').close()
        cmd = shellish.Command(name='test', run=run)
        cmd.add_file_argument('--foo', mode='r')
        cmd(argv='--foo exists')
        cmd(argv='--foo ./exists')

    def test_file_argument_create(self):
        def run(args):
            with args.foo as f:
                self.assertEqual(f.name, 'makethis')
                f.write('ascii is okay')
        cmd = shellish.Command(name='test', run=run)
        cmd.add_file_argument('--foo', mode='w')
        cmd(argv='--foo makethis')
