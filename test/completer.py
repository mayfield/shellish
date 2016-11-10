
import io
import os
import readline
import shellish
import sys
import tempfile
import unittest
from shellish.command import contrib


class ArgumentCompletions(unittest.TestCase):
    """ Test completion of argument keys. """

    def completer_sig(self, line):
        """ Convert an argument line into readline function signature. """
        spliters = readline.get_completer_delims()
        for c in spliters:  # avoid regex pitfalls with brute force splitter.
            parts = line.rsplit(c, 1)
            if len(parts) == 2:
                text = parts[1]
                break
        else:
            text = line
        return (text, line, len(line), len(line))

    def complete(self, command, args):
        line = '%s %s' % (command.prog, args)
        command.get_or_create_session()
        return command.complete(*self.completer_sig(line))

    def test_empty_shows_single_opt_arg(self):
        @shellish.autocommand
        def cmd(foo=None): pass
        self.assertEqual(self.complete(cmd, ''), {'--foo'})

    def test_valid_shows_single_opt_arg(self):
        @shellish.autocommand
        def cmd(foo=None): pass
        self.assertEqual(self.complete(cmd, '-'), {'--foo'})
        self.assertEqual(self.complete(cmd, '--'), {'--foo'})
        self.assertEqual(self.complete(cmd, '--f'), {'--foo'})
        self.assertEqual(self.complete(cmd, '--fo'), {'--foo'})
        self.assertEqual(self.complete(cmd, '--foo'), {'--foo'})

    def test_invalid_hides_single_opt_arg(self):
        @shellish.autocommand
        def cmd(foo=None): pass
        self.assertEqual(self.complete(cmd, '--nope'), set())
        self.assertEqual(self.complete(cmd, '-nope'), set())
        self.assertEqual(self.complete(cmd, 'nope'), set())
        self.assertEqual(self.complete(cmd, 'Z'), set())

    def test_single_value_argument_consumed(self):
        @shellish.autocommand
        def cmd(foo=None): pass
        self.assertEqual(self.complete(cmd, '--foo v '), set())

    def test_one_bool_argument_consumed(self):
        cmd = shellish.Command(name='cmd')
        cmd.add_argument('--foo', action='store_true')
        self.assertEqual(self.complete(cmd, '--fo'), {'--foo'})
        self.assertEqual(self.complete(cmd, '--foo'), {'--foo'})
        self.assertEqual(self.complete(cmd, '--foo '), set())

    def test_many_bool_arguments_consumed(self):
        cmd = shellish.Command(name='cmd')
        cmd.add_argument('--foo', action='store_true')
        cmd.add_argument('--bar', action='store_true')
        self.assertEqual(self.complete(cmd, '--fo'), {'--foo'})
        self.assertEqual(self.complete(cmd, '--foo'), {'--foo'})
        self.assertEqual(self.complete(cmd, '--foo '), {'--bar'})
        self.assertEqual(self.complete(cmd, '--bar '), {'--foo'})
        self.assertEqual(self.complete(cmd, '--bar --foo '), set())

    def test_one_single_value_argument_consumed(self):
        @shellish.autocommand
        def cmd(foo=None): pass
        self.assertEqual(self.complete(cmd, '--fo'), {'--foo'})
        self.assertEqual(self.complete(cmd, '--foo'), {'--foo'})
        self.assertEqual(self.complete(cmd, '--foo value '), set())

    def test_many_single_value_arguments_consumed(self):
        @shellish.autocommand
        def cmd(foo=None, bar=None): pass
        self.assertEqual(self.complete(cmd, '--fo'), {'--foo'})
        self.assertEqual(self.complete(cmd, '--foo'), {'--foo'})
        self.assertEqual(self.complete(cmd, '--foo value '), {'--bar'})
        self.assertEqual(self.complete(cmd, '--bar value '), {'--foo'})
        self.assertEqual(self.complete(cmd, '--bar value --foo value '), set())

    def test_file_arguments(self):
        cmd = shellish.Command(name='cmd')
        cmd.add_file_argument('--foo')
        with tempfile.TemporaryDirectory() as tmp:
            files = {'./one', './two'}
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                for x in files:
                    open(x, 'w').close()
                self.assertEqual(self.complete(cmd, '--foo'), {'--foo'})
                self.assertEqual(self.complete(cmd, '--foo '), files)
                self.assertEqual(self.complete(cmd, '--foo o'), {'./one'})
                self.assertEqual(self.complete(cmd, '--foo NO'), set())
            finally:
                os.chdir(cwd)

    def test_completer_custom_parser(self):
        completer = lambda *args, **kwargs: None
        class T(shellish.Command):
            def setup_args(self, parser):
                p = parser.add_mutually_exclusive_group()
                self.add_argument('--foo', parser=p, complete=completer)
        T(name='t')


class TestSysComplete(unittest.TestCase):

    def setUp(self):
        self.stdout = sys.stdout
        sys.stdout = io.StringIO()

    def tearDown(self):
        sys.stdout = self.stdout

    def test_complete_names(self):
        abc = shellish.Command(name='abc')
        xyz = shellish.Command(name='xyz')
        root = shellish.Command(name='root')
        root.add_subcommand(abc)
        root.add_subcommand(xyz)
        sc = contrib.SystemCompletion()
        root.add_subcommand(sc)
        line = 'root a'
        os.environ["COMP_CWORD"] = '1'
        os.environ["COMP_LINE"] = line
        sc(argv='--seed %s' % line)
        self.assertEqual(sys.stdout.getvalue(), 'abc\n')

    def test_complete_command_arg(self):
        abc = shellish.Command(name='abc')
        abc.add_argument('--foo')
        root = shellish.Command(name='root')
        root.add_subcommand(abc)
        sc = contrib.SystemCompletion()
        root.add_subcommand(sc)
        line = 'root abc --f'
        os.environ["COMP_CWORD"] = '2'
        os.environ["COMP_LINE"] = line
        sc(argv='--seed %s' % line)
        self.assertEqual(sys.stdout.getvalue(), '--foo\n')
