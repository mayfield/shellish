shellish
===========
_*Command-line/shell mashup framework*_

[![Maturity](https://img.shields.io/pypi/status/shellish.svg)](https://pypi.python.org/pypi/shellish)
[![License](https://img.shields.io/pypi/l/shellish.svg)](https://pypi.python.org/pypi/shellish)
[![Change Log](https://img.shields.io/badge/change-log-blue.svg)](https://github.com/mayfield/shellish/blob/master/CHANGELOG.md)
[![Build Status](https://semaphoreci.com/api/v1/mayfield/shellish/branches/master/shields_badge.svg)](https://semaphoreci.com/mayfield/shellish)
[![Version](https://img.shields.io/pypi/v/shellish.svg)](https://pypi.python.org/pypi/shellish)


About
--------

This module combines the Python standard library modules argparse and cmd
to provide a unified way to make cli programs that can also be interactive
(when invoked in "shell" mode).

The main benefit to using this package is streamlined command hierarchy when
you want to have rich set of subcommands along with a pretty powerful tab
completion layer that parses argparse arguments automagically.


Requirements
--------

Posix-like platform


Installation
--------

**PyPi Stable Release**

```
pip3 install shellish
```
    
**Development Release**

```
python3.4 ./setup.py build
python3.4 ./setup.py install
```

*or*

```
python3.4 ./setup.py develop
```

Compatibility
--------

* Python 3.4+


Examples
--------

* [Hello World](examples/hello_world.py)
* [Decorator](examples/decorator.py)
* [Nesting (Subcommands)](examples/simple_nesting.py)
* [Alternate Styles](examples/skin_a_cat.py)
* [Tab Completion](examples/tabcompletion.py)

[All Examples](examples/)
