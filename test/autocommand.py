"""
Tests for the decorator that converts a function to a command.
"""

from shellish import autocommand
import unittest


class PositionalTests(unittest.TestCase):

    def test_one_pos(self):
        @autocommand
        def f(one):
            self.assertEqual(one, 'ONE')
        f(argv='ONE')
        with self.assertRaises(SystemExit):
            f(argv='')

    def test_2_and_3_pos(self):
        @autocommand
        def f2(one, two):
            self.assertEqual(one, 'ONE')
            self.assertEqual(two, 'TWO')
        f2(argv='ONE TWO')
        with self.assertRaises(SystemExit):
            f2(argv='ONE')

        @autocommand
        def f3(one, two, three):
            self.assertEqual(one, 'ONE')
            self.assertEqual(two, 'TWO')
            self.assertEqual(three, 'THREE')
        f3(argv='ONE TWO THREE')
        with self.assertRaises(SystemExit):
            f3(argv='ONE TWO')

    def test_only_varargs(self):
        @autocommand
        def f(*args):
            self.assertEqual(args[0], 'ONE')
            self.assertEqual(args[1], 'TWO')
            self.assertEqual(len(args), 2)
        f(argv='ONE TWO')

    def test_one_pos_and_varargs(self):
        @autocommand
        def f(one, *args):
            self.assertEqual(one, 'posONE')
            self.assertEqual(args[0], 'ONE')
            self.assertEqual(args[1], 'TWO')
            self.assertEqual(len(args), 2)
        f(argv='posONE ONE TWO')

    def test_2_pos_and_varargs(self):
        @autocommand
        def f(one, two, *args):
            self.assertEqual(one, 'posONE')
            self.assertEqual(two, 'posTWO')
            self.assertEqual(args[0], 'ONE')
            self.assertEqual(args[1], 'TWO')
            self.assertEqual(len(args), 2)
        f(argv='posONE posTWO ONE TWO')

    def test_empty_varargs(self):
        @autocommand
        def f(*args):
            self.assertEqual(len(args), 0)
        f(argv='')

class KeywordTests(unittest.TestCase):

    def test_one_keyword(self):
        @autocommand
        def f(one=None):
            self.assertEqual(one, 'ONE')
        f(argv='--one ONE')

    def test_two_keywords(self):
        @autocommand
        def f(one=None, two=None):
            self.assertEqual(one, 'ONE')
            self.assertEqual(two, 'TWO')
        f(argv='--one ONE --two TWO')

    def test_only_varkwargs(self):
        @autocommand
        def f(**kwargs):
            self.assertEqual(kwargs['one'], 'ONE')
            self.assertEqual(kwargs['two'], 'TWO')
            self.assertEqual(len(kwargs), 2)
        f(argv='--kwargs --one ONE --two TWO')

    def test_onekw_and_varkwargs(self):
        @autocommand
        def f(first=None, **kwargs):
            self.assertEqual(first, 'FIRST')
            self.assertEqual(kwargs['one'], 'ONE')
            self.assertEqual(kwargs['two'], 'TWO')
            self.assertEqual(len(kwargs), 2)
        f(argv='--first FIRST --kwargs --one ONE --two TWO')

    def test_varkwargs_mixed_patterns(self):
        @autocommand
        def f(**kwargs):
            self.assertEqual(kwargs['one'], 'ONE')
            self.assertEqual(kwargs['two'], 'TWO')
            self.assertEqual(kwargs['three'], 'THREE')
            self.assertEqual(len(kwargs), 3)
        f(argv='--kwargs --one ONE --two TWO --three THREE')
        f(argv='--kwargs one=ONE two=TWO three=THREE')
        f(argv='--kwargs --one ONE two=TWO --three THREE')
        f(argv='--kwargs one=ONE --two TWO three=THREE')

    def test_empty_varkwargs(self):
        @autocommand
        def f(**kwargs):
            self.assertEqual(len(kwargs), 0)
        f(argv='')


class CombinationTests(unittest.TestCase):

    def test_arg_kwarg_varargs(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            @autocommand
            def f(one, first=None, *args):
                pass

    def test_arg_varargs_kwarg(self):
        @autocommand
        def f(one, *args, first=None):
            self.assertEqual(one, 'ONE')
            self.assertEqual(args[0], 'VONE')
            self.assertEqual(args[1], 'VTWO')
            self.assertEqual(len(args), 2)
            self.assertEqual(first, 'FIRST')
        f(argv='ONE VONE VTWO --first FIRST')

    def test_arg_varkwarg(self):
        @autocommand
        def f(one, **kwargs):
            self.assertEqual(one, 'ONE')
            self.assertEqual(kwargs['kwone'], 'KWONE')
            self.assertEqual(kwargs['kwtwo'], 'KWTWO')
            self.assertEqual(len(kwargs), 2)
        f(argv='ONE --kwargs --kwone KWONE kwtwo=KWTWO')

    def test_arg_kwarg_defaultfailback(self):
        @autocommand
        def f(one, first='DEFAULT'):
            self.assertEqual(one, 'ONE')
            self.assertEqual(first, 'DEFAULT')
        f(argv='ONE')

    def test_arg_kwarg(self):
        @autocommand
        def f(one, first='DEFAULT'):
            self.assertEqual(one, 'ONE')
            self.assertEqual(first, 'FIRST')
        f(argv='ONE --first FIRST')

    def test_arg_varargs_kwarg_varkwargs(self):
        @autocommand
        def f(one, *args, first='DEFAULT', **kwargs):
            self.assertEqual(one, 'ONE')
            self.assertEqual(args[0], 'VONE')
            self.assertEqual(args[1], 'VTWO')
            self.assertEqual(first, 'FIRST')
            self.assertEqual(kwargs['kwone'], 'KWONE')
            self.assertEqual(kwargs['kwtwo'], 'KWTWO')
            self.assertEqual(len(kwargs), 2)
        f(argv='ONE VONE VTWO --first FIRST --kwargs kwone=KWONE kwtwo=KWTWO')

    def test_empty_var_and_keyword_args(self):
        @autocommand
        def f(*args, **kwargs):
            self.assertEqual(len(args), 0)
            self.assertEqual(len(kwargs), 0)
        f(argv='')


class TypeTests(unittest.TestCase):
    """ Tests where the arguments gather type info from the function
    signature. """

    def test_annotation_str(self):
        @autocommand
        def f(one:str):
            self.assertIsInstance(one, str)
        f(argv='asdf')

    def test_annotation_bool(self):
        @autocommand
        def f(one:bool):
            self.assertIsInstance(one, bool)
        f(argv='anything_is_true_here_actually')

    def test_annotation_int(self):
        @autocommand
        def f(one:int):
            self.assertIsInstance(one, int)
            return one
        for x in [0, 1, 2**1024, -1, -2]:
            self.assertEqual(f(argv=str(x)), x)
        for x in ['nope', '0x0', '0o0']:
            with self.assertRaises(SystemExit):
                f(argv=x)

    def test_annotation_float(self):
        @autocommand
        def f(one:float):
            self.assertIsInstance(one, float)
            return one
        for x in [0, 1, 1.1]:
            self.assertEqual(f(argv=str(x)), x)
        for x in ['nope']:
            with self.assertRaises(SystemExit):
                f(argv=x)


class Nesting(unittest.TestCase):

    def test_one_level(self):
        @autocommand
        def main():
            return 'main'

        @autocommand
        def sub():
            return 'sub'

        main.add_subcommand(sub)
        self.assertEqual(main(argv=''), 'main')
        self.assertEqual(main(argv='sub'), 'sub')
