<!--
SPDX-FileCopyrightText: 2017-2019 Free Software Foundation Europe e.V.

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

## 0.4.0 - 2019-08-06

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

0.0.3 - 2017-11-06
------------------

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
