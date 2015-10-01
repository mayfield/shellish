
import readline
import shellish
import unittest


def setUpModule():
    """ Instantiate shell to get readline configured. """
    cmd = shellish.Command()
    shellish.Shell(cmd)


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

    def complete(self, command, args, remove_help=True):
        excludes = {'--help'} if remove_help else set()
        line = '%s %s' % (command.prog, args)
        return command.complete(*self.completer_sig(line)) - excludes

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
        cmd = shellish.Command()
        cmd.add_argument('--foo', action='store_true')
        self.assertEqual(self.complete(cmd, '--fo'), {'--foo'})
        self.assertEqual(self.complete(cmd, '--foo'), {'--foo'})
        self.assertEqual(self.complete(cmd, '--foo '), set())

    def test_many_bool_arguments_consumed(self):
        cmd = shellish.Command()
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
