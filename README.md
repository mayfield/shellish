shellish - Framework for creating heavy a shell-ish CLI.
===========

This module combines the Python standard library modules argparse and cmd
to provided a unified way to make cli programs that can also be interactive
when invoked in "shell" mode.

The main benefit to using this package is streamlined command hierarchy when
you want to have rich set of subcommands along with a pretty powerful tab
completion layer that parses argparse arguments automagically.

Requirements
--------

* None more black!


Installation
--------

    python3 ./setup.py build
    python3 ./setup.py install


Compatibility
--------

* Python 3.4+


TODO
--------

* Documentation
* Documentation
* Documentation


Getting Started
--------

TBD


Examples
--------

**Hello World**

A requisite Hello World..

```python
import shellish


class Hello(shellish.Command):
    """ I am a required docstring used to document the --help output! """

    name = 'hello'

    def __init__(self, *args, **kwargs):
        self.add_subcommand(World, default=True)

    def run(self, args):
        shellish.Shell(self).cmdloop()


class World(shellish.Command):
    """ Say something. """

    name = 'world'

    def run(self, args):
        print('Hello World')


if __name__ == '__main__':
    root = Hello()
    args = root.argparser.parse_args()
    try:
        root.invoke(args)
    except KeyboardInterrupt:
        sys.exit(1)
```

```bash
python3 ./hello.py hello world
```
