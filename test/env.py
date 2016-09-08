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
        c = shellish.Command()
        c.add_argument('--foo', env='FOO')
        c.run = lambda args: args
        self.assertEqual(c(argv='--foo bar').foo, 'bar')
        self.assertEqual(c(argv='').foo, None)

    def test_simple_env_set(self):
        c = shellish.Command()
        c.add_argument('--foo', env='SHELLISH_TEST_FOO')
        c.run = lambda args: args
        self.setenv('SHELLISH_TEST_FOO', 'from_env')
        self.assertEqual(c(argv='--foo from_args').foo, 'from_args')
        self.assertEqual(c(argv='').foo, 'from_env')

    def test_override_default(self):
        c = shellish.Command()
        c.add_argument('--foo', default='foodef', env='SHELLISH_TEST_FOO')
        c.run = lambda args: args
        self.assertEqual(c(argv='').foo, 'foodef')
        self.setenv('SHELLISH_TEST_FOO', 'from_env')
        self.assertEqual(c(argv='').foo, 'from_env')
        self.assertEqual(c(argv='--foo from_arg').foo, 'from_arg')

    def test_autoenv(self):
        c = shellish.Command(name="test_autoenv")
        c.add_argument('--foo', autoenv=True)
        c.run = lambda args: args
        self.assertEqual(c(argv='').foo, None)
        self.assertEqual(c(argv='--foo bar').foo, 'bar')
        self.setenv('TEST_AUTOENV_FOO', 'from_env')
        self.assertEqual(c(argv='').foo, 'from_env')
        self.assertEqual(c(argv='--foo from_arg').foo, 'from_arg')

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
