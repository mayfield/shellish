"""
A Frankenstein combo of advanced style and simple (autocommand).
"""

import shellish


@shellish.autocommand
def subcommand1(firstarg, second, *args, optional=1, optionalstr:str=None,
                mustbeint:int=None, **kwargs:bool):
    print("Hi from sub1", firstarg, second, args, optional, optionalstr,
          mustbeint, kwargs)


@shellish.autocommand
def subcommand2(firstarg, second, *args, optional=1, optionalstr:str=None,
                mustbeint:int=None, **kwargs:bool):
    print("Hi from sub2", firstarg, second, args, optional, optionalstr,
          mustbeint, kwargs)


class Root(shellish.Command):
    """ Shellify some autocommands. """

    name = 'root'

    def setup_args(self, parser):
        self.add_subcommand(subcommand1)
        self.add_subcommand(subcommand2)

root = Root()
root()
