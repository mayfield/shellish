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
- Renamed vt prefixes to vtml. ie. vtprint -> vtmlprint, etc.
- Split out table render state into its own class.  The Table class is
  used to define the config, but at render time a TableRenderer instance is
  created which holds the calculated state for a table.  This renderer state
  can be passed around and used for rendering/printing more data later.
  

### Removed
- TBD

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


[unreleased]: https://github.com/mayfield/shellish/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/mayfield/shellish/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/mayfield/shellish/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/mayfield/shellish/compare/3842251dad35c364ce3a63da04e0a5c593d1a156...v0.2.0
