# Change Log


## [Unreleased] - unreleased


## [4] - 2017-01-03
### Fixed
- Remove `foo` cruft from default log format in the new log handler.
- Cleaner help formatting when doc-strings and help kwargs are omitted.
- Removed double display of defaults when using `autocommand`.
- Workaround for flaky term size detection with docker for mac.

### Added
- Subcommand support for `env` and `autoenv` arguments.
- Sanitize autoenv generated env keys.
- Pager support for help output.
- Added contrib.tree command that shows all subcommands.

### Changed
- Default behavior of subcommand is to print help instead of just usage.
- Make name required at Command construction.


## [3] - 2016-09-14
### Added
- VTML logging handler for converting messages to VTML.
- Environment variable mapping to arguments.  Defaults or otherwise all
  argument setting can be done for arguments created with `env=NAME` or
  `autoenv=True`.
- Colorized `--help` output.
- Added default value printing to `--help` output.

### Changed
- Refactor to put vtml/html/etc into rendering submodule.
- Moved colorized traceback formatting to rendering submodule for public use.


## [2.4] - 2016-08-17
### Changed
- Arguments produced by `Command.`add_file_argument` no longer need to be
  called when used as context managers.  E.g.  In older code you would do

  ```
  with args.my_file_argument() as f:
      pass
  ```

  The new argument can be used without the invocation..
  ```
  with args.my_file_argument as f:
      pass
  ```

### Fixed
- Useful str/repr output for `Command.add_file_argument` values.


## [2.3] - 2016-08-05
### Fixed
- Docstring parsing of @autocommand commands handles omitted desc lines.
- Use `store_true` action for bool type arguments with @autocommand decorator.


## [2.2] - 2016-05-08
### Changed
- Support for setting custom config and history file names instead of
  `.(name)_config` and `.(name)_history` you can override the
  `Session.config_file` and `Session.history_file` properties.  Combined
  with setting `Session.var_dir` this allows you to store config and history
  in a sub-folder of the users home dir a la, `~/.myapp/config`.


## [2.1] - 2015-11-16
### Changed
- `Command.add_file_argument` provides a factory function instead of a file
  handle to the args namespace to avoid spontaneously creating files.
- Renamed special `command%d` argument used for command specification to
  `__command[%d]__`.

### Fixed
- File argument tab completion works in Python 3.4.


## [2] - 2015-11-04
### Changed
- Shell is now Session and does not subclass cmd.Cmd.
- `--help` is excluded from command tab completion by default.  Other args
  can also be excluded from command completion results by updating the
  `Command.completion_excludes` set. 

### Fixed
- `treeprint` can now print any standard python data types.
- Command exception handling is the same for interactive and non-captive
  modes.

### Added
- `treeprint` takes a `file` argument like `vtmlprint` and friends.
- Support for INI config files as `.<root>_config`. Also included is an
  `ini` contrib command.
- Paging support for commands or as a context manager.  Set `use_pager` to
  True on a `Command` to redirect stdout to a pager (usually less).
- The `Command` class can now be given prerun, run and postrun functions to
  be used for the resultant instance.
- Added `--no-clip` and `--table-width` options to `Table` `Command`
  arguments.

### Removed
- `vtml.is_terminal` is gone and should be replaced with direct calls to
  sys.stdout.isatty().


## [1] - 2015-10-24
### Added
- Color tags to VTML
- Argument parsing group for table formats.
- Table is a context manager that calls close when exited.
- CSV, JSON and Markdown table renderers.
- HTML to VTML parser.

### Changed
- VTML rendering of --help output;  Emboldened some elements.
- Better width handling of --help output.
- Renamed dicttree to treeprint.
- treeprint (formerly dicttree) can not print lists and dicts.

### Fixed
- VTML concatenation works with str types now.
- Plain renderer does not clip when shown on terminal.


## [0.9.0] - 2015-10-08
### Changed
- The `complete` function of `Command.add_argument` takes an args
  variable now, which is a best-effort `argparse.Namespace` of the
  arguments seen at that point in the completion life cycle.
- The table calculations for filling unspec columns now takes into
  consideration the underflow.  The leftover characters from underflow
  are redistributed to all the unspec columns evenly.
- Refactor of `TableRenderer` to be selectable by user and pluggable by
  developers.  You can register new `TableRenderer` classes for output
  formats such as HTML, etc.

### Added
- Created `data` module with caching decorators `hone_cache` and `ttl_cache`.


## [0.8.0] - 2015-10-02
### Changed
- Command now takes `title` and `desc` instead of `doc` argument.
- A Command subclass is not required to provide a docstring.


## [0.7.0] - 2015-10-01
### Added
- Support for disabling tab completion padding (adding a space after single
  matches).
- Tests for tab completion.
- Added Command.postrun() to match existing prerun() hook (with caveat noted
  below). 

### Changed
- Only run Command.prerun on the instance being 'run()'.
- Change VTML 'UL' tag to just 'U' to match html spec and avoid confusion

### Fixed
- Tab completion does not double-add optional argument keys when they have
  been satisfied already.  This partially worked before with an off-by-1-ish
  error.
- Cleanup for padding code to not strip argument values which are delimited.


## [0.6.0] - 2015-09-23
### Added
- System wide tab completion support via npm style 'completion' bootstrap
  command.


## [0.5.1] - 2015-09-18
### Changed
- Nothing, just SCM/deploy testing.


## [0.5.0] - 2015-09-13
### Added
- Custom per/user configuration file reader.
- Custom prompt using ^
- Per/column style for table.
  You can set padding, width, minwidth, and align settings on each column

### Changed
- `Command.shell()` renamed to Command.interact()
- `Command.inject_context` accepts a dictionary or kwargs and will cascade
  new values to subcommands.
- Renamed vt prefixes to vtml. ie. `vtprint` -> `vtmlprint`, etc.
- Split out table render state into its own class.  The Table class is
  used to define the config, but at render time a TableRenderer instance is
  created which holds the calculated state for a table.  This renderer state
  can be passed around and used for rendering/printing more data later.
- Renamed `Table.write` to `Table.print` (same for `write_row`).
- Renamed `Table(column_spec=None)` to just columns.
- `Table(column_spec)` is now optional.
  
### Fixed
- Table handling for vtml strings that overflow.
- Column padding is applied to left and right of the inner data now.
- Column minwidth handling fixed when no clipping was required.


## [0.4.0] - 2015-09-09
### Fixed
- vtprint hardening (it will degrade quietly when the parser fails).

### Added
- Tree printer and convenience dicttree helper function.
- Configurable exception handling for Shell.


## [0.3.0] - 2015-09-04
### Added
- Table support
- vt100 capable printer for bold, underline, etc.


## [0.2.0] - 2015-08-28
### Changed
- First stable release


[unreleased]: https://github.com/mayfield/shellish/compare/v4...HEAD
[4]: https://github.com/mayfield/shellish/compare/v3...v4
[3]: https://github.com/mayfield/shellish/compare/v2.4...v3
[2.4]: https://github.com/mayfield/shellish/compare/v2.3...v2.4
[2.3]: https://github.com/mayfield/shellish/compare/v2.2...v2.3
[2.2]: https://github.com/mayfield/shellish/compare/v2.1...v2.2
[2.1]: https://github.com/mayfield/shellish/compare/v2...v2.1
[2]: https://github.com/mayfield/shellish/compare/v1...v2
[1]: https://github.com/mayfield/shellish/compare/v0.9.0...v1
[0.9.0]: https://github.com/mayfield/shellish/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/mayfield/shellish/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/mayfield/shellish/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/mayfield/shellish/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/mayfield/shellish/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/mayfield/shellish/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/mayfield/shellish/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/mayfield/shellish/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/mayfield/shellish/compare/3842251dad35c364ce3a63da04e0a5c593d1a156...v0.2.0
