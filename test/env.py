import shellish
import unittest
import os


class EnvTests(unittest.TestCase):

    def setUp(self):
        self.env_save = env = os.environ
        os.environ = env.copy()

    def tearDown(self):
        os.environ = self.env_save

    def setenv(self, key, value):
        os.environ[key] = value

    def test_simple_env_noset(self):
        c = shellish.Command(name='c')
        c.add_argument('--foo', env='FOO')
        c.run = lambda args: args
        self.assertEqual(c(argv='--foo bar').foo, 'bar')
        self.assertEqual(c(argv='').foo, None)

    def test_dup_env(self):
        c = shellish.Command(name='c')
        c.add_argument('--foo', env='FOO')
        self.assertRaises(ValueError, c.add_argument, '--bar', env='FOO')

    def test_simple_env_set(self):
        c = shellish.Command(name='c')
        c.add_argument('--foo', env='SHELLISH_TEST_FOO')
        c.run = lambda args: args
        self.setenv('SHELLISH_TEST_FOO', 'from_env')
        self.assertEqual(c(argv='--foo from_args').foo, 'from_args')
        self.assertEqual(c(argv='').foo, 'from_env')

    def test_override_default(self):
        c = shellish.Command(name='c')
        c.add_argument('--foo', default='foodef', env='SHELLISH_TEST_FOO')
        c.run = lambda args: args
        self.assertEqual(c(argv='').foo, 'foodef')
        self.setenv('SHELLISH_TEST_FOO', 'from_env')
        self.assertEqual(c(argv='').foo, 'from_env')
        self.assertEqual(c(argv='--foo from_arg').foo, 'from_arg')

    def test_autoenv(self):
        c = shellish.Command(name="test_autoenv")
        c.add_argument('--foo', autoenv=True)
        c.run = lambda args: args  # just return args ns
        self.assertEqual(c(argv='').foo, None)
        self.assertEqual(c(argv='--foo bar').foo, 'bar')
        self.setenv('TEST_AUTOENV_FOO', 'from_env')
        self.assertEqual(c(argv='').foo, 'from_env')
        self.assertEqual(c(argv='--foo from_arg').foo, 'from_arg')

    def test_autoenv_nested_commands(self):
        head = shellish.Command(name="head")
        tail = shellish.Command(name="tail")
        tail.add_argument('--foo', autoenv=True)
        head.add_subcommand(tail)
        tail.run = lambda args: args  # just return args ns
        self.assertEqual(head(argv='tail').foo, None)
        self.assertEqual(head(argv='tail --foo bar').foo, 'bar')
        self.setenv('HEAD_TAIL_FOO', 'from_env')
        self.assertEqual(head(argv='tail').foo, 'from_env')
        self.assertEqual(head(argv='tail --foo from_arg').foo, 'from_arg')

    def test_autoenv_double_nested_commands(self):
        head = shellish.Command(name="head")
        mid = shellish.Command(name="mid")
        tail = shellish.Command(name="tail")
        tail.add_argument('--foo', autoenv=True)
        mid.add_subcommand(tail)
        head.add_subcommand(mid)
        tail.run = lambda args: args  # just return args ns
        self.assertEqual(head(argv='mid tail').foo, None)
        self.assertEqual(head(argv='mid tail --foo bar').foo, 'bar')
        self.setenv('HEAD_MID_TAIL_FOO', 'from_env')
        self.assertEqual(head(argv='mid tail').foo, 'from_env')
        self.assertEqual(head(argv='mid tail --foo from_arg').foo, 'from_arg')

    def test_autoenv_double_nested_commands_alt_order(self):
        head = shellish.Command(name="head")
        mid = shellish.Command(name="mid")
        head.add_subcommand(mid)
        tail = shellish.Command(name="tail")
        mid.add_subcommand(tail)
        tail.add_argument('--foo', autoenv=True)
        tail.run = lambda args: args  # just return args ns
        self.assertEqual(head(argv='mid tail').foo, None)
        self.assertEqual(head(argv='mid tail --foo bar').foo, 'bar')
        self.setenv('HEAD_MID_TAIL_FOO', 'from_env')
        self.assertEqual(head(argv='mid tail').foo, 'from_env')
        self.assertEqual(head(argv='mid tail --foo from_arg').foo, 'from_arg')

    def test_autoenv_odd_names(self):
        names = {
            "test-autoenv": "TEST_AUTOENV",
            "test ": "TEST",
            "test  ": "TEST",
            " test  ": "TEST",
            " test": "TEST",
            "  test": "TEST",
            "  test-test": "TEST_TEST",
            "  test test": "TEST_TEST",
            "  t!@#$est-test": "TEST_TEST",
            "1test": "_1TEST",
            " 1test": "_1TEST",
            " 1test ": "_1TEST",
        }
        for i, (name, env_prefix) in enumerate(names.items()):
            with self.subTest(name):
                c = shellish.Command(name=name)
                action = c.add_argument('--foo', autoenv=True)
                self.assertEqual(action.env, '%s_FOO' % env_prefix)

    def test_nonstd_parser(self):
        c = shellish.Command(name="test_autoenv")
        g = c.argparser.add_mutually_exclusive_group()
        c.add_argument('--foo', parser=g, env='SHELLISH_TEST_FOO')
        c.run = lambda args: args
        self.assertEqual(c(argv='').foo, None)
        self.assertEqual(c(argv='--foo bar').foo, 'bar')
        self.setenv('SHELLISH_TEST_FOO', 'from_env')
        self.assertEqual(c(argv='').foo, 'from_env')
        self.assertEqual(c(argv='--foo from_arg').foo, 'from_arg')
