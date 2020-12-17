<!--
SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# Change log

This change log follows the [Keep a
Changelog](http://keepachangelog.com/) spec. Every release contains the
following sections:

-   `Added` for new features.
-   `Changed` for changes in existing functionality.
-   `Deprecated` for soon-to-be removed features.
-   `Removed` for now removed features.
-   `Fixed` for any bug fixes.
-   `Security` in case of vulnerabilities.

The versions follow [semantic versioning](https://semver.org).

<!--
## Unreleased - YYYY-MM-DD

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security
-->

## 0.12.1 - 2020-12-17

### Fixed

- Bumped versions of requirements (#288).

## 0.12.0 - 2020-12-16

This release was delayed due to the absence of the lead developer (Carmen, me,
the person writing these release notes). Many thanks to Max Mehl for
coordinating the project in my absence. Many thanks also to the contributors who
sent in pull requests, in reverse chronological order: Olaf Meeuwissen, Mikko
Piuola, Wolfgang Traylor, Paul Spooren, Robert Cohn, ethulhu, pukkamustard, and
Diego Elio Pettenò.

### Added

- Separate Docker image with additional executables installed
  (`fsfe/reuse:latest-extra`) (#238)

- Allow different styles of copyright lines: SPDX (default), String, String (C),
  String ©, and © (#248)

- Convenience function to update resources (SPDX license list and exceptions)
  (#268)

- More file types are recognised:
  + ClojureScript (`.cljc`, `.cljs`)
  + Fortran (`.F`, `.F90`, `.f90`, `.f95`, `.f03`, `.f`, `.for`)
  + Makefile (`.mk`)
  + PlantUML (`.iuml`, `.plantuml`, `.pu`, `.puml`)
  + R (`.R`, `.Renviron`, `.Rprofile`)
  + ReStructured Text (`.rst`)
  + RMarkdown (`.Rmd`)
  + Scheme (`.scm`)
  + TypeScript (`.ts`)
  + TypeScript JSX (`.tsx`)
  + Windows Batch (`.bat`)

- More file names are recognised:
  + .dockerignore
  + Gemfile
  + go.mod
  + meson.build
  + Rakefile

### Changed

- Use UTF-8 explicitly when reading files (#242)

### Fixed

- Updated license list to 3.11.

## 0.11.1 - 2020-06-08

### Fixed

- Similar to CAL-1.0 and CAL-1.0-Combined-Work-Exception, SHL-2.1 is now ignored
  because it contains an SPDX tag within itself.

## 0.11.0 - 2020-05-25

### Added

- Added `--skip-unrecognised` flag to `addheader` in order to skip files with
  unrecognised comment styles instead of aborting without processing any file.

### Changed

- Always write the output files encoded in UTF-8, explicitly. This is already the
  default on most Unix systems, but it was not on Windows.

- All symlinks and 0-sized files in projects are now ignored.

### Fixed

- The licenses CAL-1.0 and CAL-1.0-Combined-Work-Exception contain an SPDX tag
  within themselves. Files that are named after these licenses are now ignored.

- Fixed a bug where `addheader` wouldn't properly apply the template on
  `.license` files if the `.license` file was non-empty, but did not contain
  valid SPDX tags.

## 0.10.1 - 2020-05-14

### Fixed

- Updated license list to 3.8-106-g4cfec76.

## 0.10.0 - 2020-04-24

### Added

- Add support for autoconf comment style (listed as m4).

- More file types are recognised:

  + Cython (`.pyx`, `.pxd`)
  + Sass and SCSS (`.sass`, `.scss`)
  + XSL (`.xsl`)
  + Mailmap (`.mailmap`)

- Added `--single-line` and `--multi-line` flags to `addheader`. These flags
  force a certain comment style.

### Changed

- The Docker image has an entrypoint now. In effect, this means running:

 `docker run -v $(pwd):/data fsfe/reuse lint`

 instead of

 `docker run -v $(pwd):/data fsfe/reuse reuse lint`.

## 0.9.0 - 2020-04-21

### Added

- Added support for Mercurial 4.3+.

- A pre-commit hook has been added.

- When an incorrect SPDX identifier is forwarded to `download` or `init`, the
  tool now suggests what you might have meant.

### Changed

- Under the hood, a lot of code that has to do with Git and Mercurial was moved
  into its own module.

- The Docker image has been changed such that it now automagically runs `reuse
  lint` on the `/data` directory unless something else is specified by the user.

### Fixed

- Fixed a bug with `addheader --explicit-license` that would result in
  `file.license.license` if `file.license` already existed.

- Fixed a Windows-only bug to do with calling subprocesses.

- Fixed a rare bug that would trigger when a directory is both ignored and
  contains a `.git` file.

## 0.8.1 - 2020-02-22

### Added

- Support Jinja (Jinja2) comment style.

- Support all multi-line comment endings when parsing for SPDX information.

### Fixed

- Improvements to German translation by Thomas Doczkal.

- No longer remove newlines at the end of files when using `addheader`.

- There can now be a tab as whitespace after `SPDX-License-Identifier` and
  `SPDX-FileCopyrightText`.

## 0.8.0 - 2020-01-20

### Added

- Implemented `--root` argument to specify the root of the project without
  heuristics.

- The linter will complain about licenses without file extensions.

- Deprecated licenses are now recognised. `lint` will complain about deprecated
  licenses.

- ProjectReport generation (`lint`, `spdx`) now uses Python multiprocessing,
  more commonly called multi-threading outside of Python. This has a significant
  speedup of approximately 300% in testing. Because of overhead, performance
  increase is not exactly linear.

- For setups where multiprocessing is unsupported or unwanted,
  `--no-multiprocessing` is added as flag.

- `addheader` now recognises many more extensions. Too many to list here.

- `addheader` now also recognises full filenames such as `Makefile` and
  `.gitignore`.

- Added BibTex comment style.

- Updated translations:

  + Dutch (André Ockers, Carmen Bianca Bakker)
  + French (OliBug, Vincent Lequertier)
  + Galician (pd)
  + German (Max Mehl)
  + Esperanto (Carmen Bianca Bakker)
  + Portuguese (José Vieira)
  + Spanish (Roberto Bauglir)
  + Turkish (T. E. Kalayci)

### Changed

- The linter output has been very slightly re-ordered to be more internally
  consistent.

- `reuse --version` now prints a version with a Git hash on development
  versions. Towards that end, the tool now depends on `setuptools-scm` during
  setup. It is not a runtime dependency.

### Removed

- `lint` no longer accepts path arguments. Where previously one could do `reuse
  lint SUBDIRECTORY`, this is no longer possible. When linting, you must always
  lint the entire project. To change the project's root, use `--root`.

- `FileReportInfo` has been removed. `FileReport` is used instead.

### Fixed

- A license that does not have a file extension, but whose full name is a valid
  SPDX License Identifier, is now correctly identified as such. The linter will
  complain about them, however.

- If the linter detects a license as being a bad license, that license can now
  also be detected as being missing.

- Performance of `project.all_files()` has been improved by quite a lot.

- Files with CRLF line endings are now better supported.

## 0.7.0 - 2019-11-28

### Changed

- The program's package name on PyPI has been changed from `fsfe-reuse` to
  `reuse`. `fsfe-reuse==1.0.0` has been created as an alias that depends on
  `reuse`. `fsfe-reuse` will not receive any more updates, but will still host
  the old versions.

- For users of `fsfe-reuse`, this means:

  + If you depend on `fsfe-reuse` or `fsfe-reuse>=0.X.Y` in your
    requirements.txt, you will get the latest version of `reuse` when you
    install `fsfe-reuse`. You may like to change the name to `reuse` explicitly,
    but this is not strictly necessary.

  + If you depend on `fsfe-reuse==0.X.Y`, then you will keep getting that
    version. When you bump the version you depend on, you will need to change
    the name to `reuse`.

  + If you depend on `fsfe-reuse>=0.X.Y<1.0.0`, then 0.6.0 will be the latest
    version you receive. In order to get a later version, you will need to
    change the name to `reuse`.

## 0.6.0 - 2019-11-19

### Added

- `--include-submodules` is added to also include submodules when linting et
  cetera.

- `addheader` now also recognises the following extensions:

  + .kt
  + .xml
  + .yaml
  + .yml

### Changed

- Made the workaround for `MachineReadableFormatError` introduced in 0.5.2 more
  generic.

- Improved shebang detection in `addheader`.

- For `addheader`, the SPDX comment block now need not be the first thing in the
  file. It will find the SPDX comment block and deal with it in-place.

- Git submodules are now ignored by default.

- `addheader --explicit-license` now no longer breaks on unsupported filetypes.

## 0.5.2 - 2019-10-27

### Added

- `python3 -m reuse` now works.

### Changed

- Updated license list to 3.6-2-g2a14810.

### Fixed

- Performance of `reuse lint` improved by at least a factor of 2. It no longer
  does any checksums on files behind the scenes.

- Also handle `MachineReadableFormatError` when parsing DEP5 files. Tries to
  import that error. If the import is unsuccessful, it is handled.

## 0.5.1 - 2019-10-24 [YANKED]

This release was replaced by 0.5.2 due to importing
`MachineReadableFormatError`, which is not a backwards-compatible change.

## 0.5.0 - 2019-08-29

### Added

- TeX and ML comment styles added.

- Added `--year` and `--exclude-year` to `reuse addheader`.

- Added `--template` to `reuse addheader`.

- Added `--explicit-license` to `reuse addheader`.

- `binaryornot` added as new dependency.

- Greatly improved the usage documentation.

### Changed

- `reuse addheader` now automatically adds the current year to the copyright
  notice.

- `reuse addheader` preserves the original header below the new header if it did
  not contain any SPDX information.

- `reuse addheader` now correctly handles `.license` files.

- Bad licenses are no longer resolved to LicenseRef-Unknown<n>. They are instead
  resolved to the stem of the path. This reduces the magic in the code base.

- `.gitkeep` files are now ignored by the tool.

- Changed Lisp's comment character from ';;' to ';'.

## 0.4.1 - 2019-08-07

### Added

- `--all` argument help to `reuse download`, which downloads all detected
  missing licenses.

### Fixed

- When using `reuse addheader` on a file that contains a shebang, the shebang is
  preserved.

- Copyright lines in `reuse spdx` are now sorted.

- Some publicly visible TODOs were patched away.

## 0.4.0 - 2019-08-07

This release is a major overhaul and refactoring of the tool. Its
primary focus is improved usability and speed, as well as adhering to version
3.0 of the REUSE Specification.

### Added

- `reuse addheader` has been added as a way to automatically add copyright
  statements and license identifiers to the headers of files. It is currently
  not complete.

- `reuse init` has been added as a way to initialise a REUSE project. Its
  functionality is currently scarce, but should improve in the future.

### Changed

- `reuse lint` now provides a helpful summary instead of merely spitting out
  non-compliant files.

- `reuse compile` is now `reuse spdx`.

- In addition to `Copyright` and `©`, copyright lines can be marked with the tag
  `SPDX-FileCopyrightText:`. This is the new recommended default.

- Project no longer depends on pygit2.

- The list of SPDX licenses has been updated.

- `Valid-License-Identifier` is no longer used, and licenses and exceptions can
  now only live inside of the LICENSES/ directory.

### Removed

- Removed `--ignore-debian`.

- Removed `--spdx-mandatory`, `--copyright-mandatory`, `--ignore-missing`
  arguments from `reuse lint`.

- Remove `reuse license`.

- GPL-3.0 and GPL-3.0+ (and all other similar GPL licenses) are no longer
  detected as SPDX identifiers. Use GPL-3.0-only and GPL-3.0-or-later instead.

### Fixed

- Scanning a Git directory is a lot faster now.

- Scanning binary files is a lot faster now.

## 0.3.4 - 2019-04-15

This release should be a short-lived one. A new (slightly
backwards-incompatible) version is in the works.

### Added

-   Copyrights can now start with `©` in addition to `Copyright`. The
    former is now recommended, but they are functionally similar.

### Changed

-   The source code of reuse is now formatted with black.
-   The repository has been moved from
    <https://git.fsfe.org/reuse/reuse> to
    <https://gitlab.com/reuse/reuse>.

## 0.3.3 - 2018-07-15

### Fixed

-   Any files with the suffix `.spdx` are no longer considered licenses.

## 0.3.2 - 2018-07-15

### Fixed

-   The documentation now builds under Python 3.7.

## 0.3.1 - 2018-07-14

### Fixed

-   When using reuse from a child directory using pygit2, correctly find
    the root.

## 0.3.0 - 2018-05-16

### Changed

-   The output of `reuse compile` is now deterministic. The files,
    copyright lines and SPDX expressions are sorted alphabetically.

### Fixed

-   When a GPL license could not be found, the correct `-only` or
    `-or-later` extension is now used in the warning message, rather
    than a bare `GPL-3.0`.
-   If you have a license listed as
    `SPDX-Valid-License: GPL-3.0-or-later`, this now correctly matches
    corresponding SPDX identifiers. Still it is recommended to use
    `SPDX-Valid-License: GPL-3.0` instead.

## 0.2.0 - 2018-04-17

### Added

-   Internationalisation support added. Initial support for:
    -   English.
    -   Dutch.
    -   Esperanto.
    -   Spanish.

### Fixed

-   The license list of SPDX 3.0 has deprecated `GPL-3.0` and `GPL-3.0+`
    et al in favour of `GPL-3.0-only` and `GPL-3.0-or-later`. The
    program has been amended to accommodate sufficiently for those
    licenses.

### Changed

-   `Project.reuse_info_of` now extracts, combines and returns
    information both from the file itself and from debian/copyright.
-   `ReuseInfo` now holds sets instead of lists.
    -   As a result of this, `ReuseInfo` will not hold duplicates of
        copyright lines or SPDX expressions.
-   click removed as dependency. Good old argparse from the library is
    used instead.

## 0.1.1 - 2017-12-14

### Changed

-   The `reuse --help` text has been tidied up a little bit.

### Fixed

-   Release date in change log fixed.
-   The PyPI homepage now gets reStructuredText instead of Markdown.

## 0.1.0 - 2017-12-14

### Added

-   Successfully parse old-style C and HTML comments now.
-   Added `reuse compile`, which creates an SPDX bill of materials.
-   Added `--ignore-missing` to `reuse lint`.
-   Allow to specify multiple paths to `reuse lint`.
-   `chardet` added as dependency.
-   `pygit2` added as soft dependency. reuse remains usable without it,
    but the performance with `pygit2` is significantly better. Because
    `pygit2` has a non-Python dependency (`libgit2`), it must be
    installed independently by the user. In the future, when reuse is
    packaged natively, this will not be an issue.

### Changed

-   Updated to version 2.0 of the REUSE recommendations. The
    most important change is that `License-Filename` is no longer used.
    Instead, the filename is deducted from `SPDX-License-Identifier`.
    This change is **NOT** backwards compatible.
-   The conditions for linting have changed. A file is now non-compliant
    when:
    -   The license associated with the file could not be found.
    -   There is no SPDX expression associated with the file.
    -   There is no copyright notice associated with the file.
-   Only read the first 4 KiB (by default) from code files rather than
    the entire file when searching for SPDX tags. This speeds up the
    tool a bit.
-   `Project.reuse_info_of` no longer raises an exception. Instead, it
    returns an empty `ReuseInfo` object when no reuse information is
    found.
-   Logging is a lot prettier now. Only output entries from the `reuse`
    module.

### Fixed

-   `reuse --ignore-debian compile` now works as expected.
-   The tool no longer breaks when reading a file that has a non-UTF-8
    encoding. Instead, `chardet` is used to detect the encoding before
    reading the file. If a file still has errors during decoding, those
    errors are silently ignored and replaced.

## 0.0.4 - 2017-11-06

### Fixed

-   Removed dependency on `os.PathLike` so that Python 3.5 is actually
    supported

## 0.0.3 - 2017-11-06

### Fixed

-   Fixed the link to PyPI in the README.

## 0.0.2 - 2017-11-03

This is a very early development release aimed at distributing the
program as soon as possible. Because this is the first release, the
changelog is a little empty beyond "created the program".

The program can do roughly the following:

-   Detect the license of a given file through one of three methods (in
    order of precedence):
    -   Information embedded in the .license file.
    -   Information embedded in its header.
    -   Information from the global debian/copyright file.
-   Find and report all files in a project tree of which the license
    could not be found.
-   Ignore files ignored by Git.
-   Do some logging into STDERR.
