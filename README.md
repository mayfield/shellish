shellish - Command-line/shell mashup framework. 
===========

This module combines the Python standard library modules argparse and cmd
to provide a unified way to make cli programs that can also be interactive
(when invoked in "shell" mode).

The main benefit to using this package is streamlined command hierarchy when
you want to have rich set of subcommands along with a pretty powerful tab
completion layer that parses argparse arguments automagically.

Status
--------

[![Change Log](https://img.shields.io/badge/change-log-blue.svg)](https://github.com/mayfield/shellish/blob/master/CHANGELOG.md)
[![Build Status](https://semaphoreci.com/api/v1/projects/d925ee35-bede-4cc1-bbb8-17a738b84cfa/533600/shields_badge.svg)](https://semaphoreci.com/mayfield/shellish)


Requirements
--------

* None more black!


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

* [Hello World](examples/hello_world.py)
* [Decorator](examples/decorator.py)
* [Nesting (Subcommands)](examples/simple_nesting.py)
* [Alternate Styles](examples/skin_a_cat.py)
* [Tab Completion](examples/tabcompletion.py)

--------
[All Examples](examples/)
