# Change Log


## [Unreleased] - unreleased
### Added
- Custom per/user configuration file reader.
- Custom prompt using ^
- Per/column style for table.
  You can set padding, width, minwidth, and align settings on each column

### Changed
- Command.shell() renamed to Command.interact()
- Command.inject_context accepts a dictionary or kwargs and will cascade
  new values to subcommands.

### Removed
- TBD

### Fixed
- Table handling for vtml strings that overflow.


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


[unreleased]: https://github.com/mayfield/shellish/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/mayfield/shellish/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/mayfield/shellish/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/mayfield/shellish/compare/3842251dad35c364ce3a63da04e0a5c593d1a156...v0.2.0
