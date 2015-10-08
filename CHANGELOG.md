# Change Log

## [Unreleased] - unreleased

## [0.9.0] - 2015-10-08
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
- Command.shell() renamed to Command.interact()
- Command.inject_context accepts a dictionary or kwargs and will cascade
  new values to subcommands.
- Renamed vt prefixes to vtml. ie. vtprint -> vtmlprint, etc.
- Split out table render state into its own class.  The Table class is
  used to define the config, but at render time a TableRenderer instance is
  created which holds the calculated state for a table.  This renderer state
  can be passed around and used for rendering/printing more data later.
- Renamed Table.write to Table.print (same for write_row).
- Renamed Table(column_spec=None) to just columns.
- Table(column_spec) is now optional.
  
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


[unreleased]: https://github.com/mayfield/shellish/compare/v0.9.0...HEAD
[0.9.0]: https://github.com/mayfield/shellish/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/mayfield/shellish/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/mayfield/shellish/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/mayfield/shellish/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/mayfield/shellish/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/mayfield/shellish/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/mayfield/shellish/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/mayfield/shellish/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/mayfield/shellish/compare/3842251dad35c364ce3a63da04e0a5c593d1a156...v0.2.0
