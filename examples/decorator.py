"""
Decorate a function that uses keyword arguments.
"""

import shellish


@shellish.autocommand
def hello(firstarg, second, *args, optional=1, optionalstr:str=None,
          mustbeint:int=None, **kwargs:bool):
    print("Hello", firstarg, second, args, optional, optionalstr,
          mustbeint, kwargs)

hello()
