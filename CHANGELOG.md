<!--
SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
SPDX-FileCopyrightText: 2023 DB Systel GmbH
SPDX-FileCopyrightText: 2024 Rivos Inc.
SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# Change log

This change log follows the [Keep a Changelog](http://keepachangelog.com/) spec.
Every release contains the following sections:

- `Added` for new features.
- `Changed` for changes in existing functionality.
- `Deprecated` for soon-to-be removed features.
- `Removed` for now removed features.
- `Fixed` for any bug fixes.
- `Security` in case of vulnerabilities.

The versions follow [semantic versioning](https://semver.org) for the `reuse`
CLI command and its behaviour. There are no guarantees of stability for the
`reuse` Python library.

<!-- protokolo-section-tag -->

## v6.1.0 - 2025-10-07

This release adds a simple feature as a workaround for a bug that will be
resolved in a later version. The bug is described in
<https://github.com/fsfe/reuse-tool/issues/1244>, and can be summarised as: When
`charset-normalizer` is used to detect the encoding of a file, it will
erroneously detect a UTF-8 file as having no encoding (i.e. a binary file) when
the 2048th byte is a non-final byte of a multi-byte glyph.

You can run reuse as `REUSE_ENCODING_MODULE=chardet reuse` to circumvent this
bug. If you use pre-commit, you can use this snippet:

```yaml
repos:
  - repo: https://github.com/fsfe/reuse-tool
    rev: v6.1.0
    hooks:
      - id: reuse
        entry: env REUSE_ENCODING_MODULE=chardet reuse
```

You will not encounter this bug if your environment has libmagic available.

### Added

- You can now specify the module that will be used for detecting the encoding of
  files with the `REUSE_ENCODING_MODULE` environment variable. (#1245)
- The Docker images and the pre-commit hooks now come bundled with all encoding
  modules. (#1245)
- The `--debug` flag now tells you the detected encoding and detected newlines
  of each file, as well as which encoding module is used. (#1246)

## v6.0.0 - 2025-10-06

This release contains a lot of refactoring regarding the parsing of files. The
most impactful details are that `reuse lint` now searches every file in its
entirety for REUSE information, tries to detect each file's encoding, and no
longer breaks when invalid SPDX License Expressions are detected.

Because files are now read in their entireties instead of just the first 4 KiB,
you may need to add `REUSE-IgnoreStart` and `REUSE-IgnoreEnd` tags to get rid of
false positives that were previously too deep into files for `reuse` to detect.

**For package maintainers:** This release removes, adds, and changes
dependencies. It merits running `git diff v5.1.1..v6.0.0 pyproject.toml` and
reading the 'Changed' section of this change log to see what changed.

### Added

- Added new file extensions:
  - `py.typed` (#1239)
  - `.blade.php` (#573)
- A new criterion 'Invalid SPDX License Expressions' has been added to
  `reuse lint`. Invalid expressions are SPDX License Expressions which are not
  valid according to the grammar of the SPDX specification. (#1240)

### Changed

- Python 3.9 support dropped. (#1219)
- The Python requirement for `reuse` now no longer requires a lower major
  version than 4. The requirement is now `>=3.10` instead of `>=3.10,<4`.
  (#1219)
- Dependency changes:
  - Removed explicit dependency `boolean.boolean`. It is now an implicit
    dependency via `license-expression`. (#1240)
  - The dependency `python-magic` has been added, alongside the optional
    dependencies `charset-normalizer` and `chardet`. So long as at least one of
    these is installed, the program will work. (#1235)
  - The dependency `binaryornot` has been removed. (#1235)
  - The minimum requirements of several dependencies have been updated. (#1235,
    #1241)
- `reuse lint` now always searches the entire file for REUSE information.
  Previously, it only searched the first 4 KiB under most circumstances. (#1229)
- The encodings of files are now detected before they are read or altered.
  (#1235, #1218)
- The 'Bad licenses' criterion in `reuse lint` previously searched for bad
  licenses in every single file. Now, only bad licenses in `LICENSES/` are
  detected, which is more in line with the documentation. (#1240)
- The behaviour of the `--year` option to `reuse annotate`is now different.
  Previously, you could define `--year <year>` multiple times. Now you can only
  do so once, but the value may be a string containing multiple years or a range
  of years. (#1145)
- `reuse annotate --merge-copyrights` works more efficiently now, capable of
  better heuristics to detect years and year ranges. (#1145)
- `reuse annotate --merge-copyrights` no longer adds spacing around the merged
  year ranges. i.e. `2017-2025`, not `2017 - 2025`. (#1145)

### Fixed

- Unparseable SPDX expressions in a file now no longer cause the collection of
  REUSE information from that file to entirely fail. (#1240)
- Files with carriage return (`\r`) line endings are now correctly linted.
  (#1235, #1226)
- There used to be a specific scenario where `reuse lint` would read the
  contents of an entire file into memory. This no longer happens.
  `reuse annotate` will still read the entire file into memory. (#1229)
- Fixed formatting in `lint` subcommand help message. (#1212, #1236)
- Fixed a case where, if a recognised file extension (such as `.blade.php`) has
  two or more components, it would not be correctly recognised. (#573)
- Fixed a bug where, if `REUSE-IgnoreStart` is the very first thing that appears
  in a file, the subsequent text is not actually ignored. (#1229)
- If using `reuse annotate` to write to a file, the BOM is preserved if the
  encoding is UTF-8, UTF-16, or UTF-32. (#1235, #384)
- The summaries of `reuse lint` are now sorted better. (#1241)
- Several performance improvements. Local testing on a 12-core laptop suggests
  speedup of up to 50%, but it may depend on your repository. (#1222, #1223,
  #1230, #1241)

## v5.1.1 - 2025-09-05

### Fixed

- Fixed repository file detection using jujutsu versions 0.19.0 or later.
  (#1191)
- Fixed a bug that caused not all strings to be marked translatable. This bug
  was introduced in v5.0.0. Strings that were already translated _before_ the
  release of v5.0.0 are now translated again. (#1216)

## v5.1.0 - 2025-09-04

### Added

- Added new file extensions:
  - `.dtd` (#1141)
  - `.gperf` (#1131)
  - Erlang `.erl` and `.hrl`, leex and yecc Erlang parser generators `.xrl` and
    `.yrl` (#1117)
  - Elixir (`.ex` and `.exs`) (#1117)
  - Gleam (`.gleam`) (#1117)
  - Lean (`.lean`, `.olean`, and `.ilean`) (#1188)
- Added `--json` flag to the `supported-licenses` subcommand. (#1187)

### Changed

- Revert `Cargo.lock` to uncommentable. (#1169)
- `reuse annotate` previously would insert a newline after a header, which is
  not always a desirable behavior. Instead of inserting a newline,
  `reuse annotate` will now respect the existing whitespace of the file where
  the header is being placed. When the license header is being added to a file
  for the first time, a space will be added after the license, but subsequent
  updates to the header will leave the whitespace alone. (#1136)
- Updated `spdx-license-list-data` to v3.27.0.

## v5.0.2 - 2024-11-14

### Fixed

- The release date for the v5.0.0 entry in the change log was wrong.

## v5.0.1 - 2024-11-14

### Fixed

- Fix readthedocs build.

## v5.0.0 - 2024-11-14

This is a big release for a small change set. With this release, the tool
becomes compatible with
[REUSE Specification 3.3](https://reuse.software/spec-3.3), which is a very
subtly improved release of the much bigger version 3.2.

### Added

- More file types are recognised:
  - Cabal (`.cabal`, `cabal.project`) (#1089, #1090)
  - `.envrc` (#1061)
  - `.flake.lock` (#1061)
  - Ansible Jinja2 (`.j2`) (#1036)
  - Poetry lock file (`poetry.lock`) (#1037)
- Added `lint-file` subcommand to enable running lint on specific files. (#1055)
- Added shell completion via `click`. (#1084)
- Added Jujutsu VCS support. (#1051)
- Added new copyright prefixes `spdx-string`, `spdx-string-c`, and
  `spdx-string-symbol`. (#979)
- Support for Python 3.13. (#1092)

### Changed

- Bumped REUSE Specification version to
  [version 3.3](https://reuse.software/spec-3.3). (#1069)
- Switched from `argparse` to `click` for handling the CLI. The CLI should still
  handle the same, with identical options and arguments, but some stuff changed
  under the hood. (#1084)

  Find here a small list of differences:

  - `-h` is no longer shorthand for `--help`.
  - `--version` now outputs "reuse, version X.Y.Z", followed by a licensing
    blurb on different paragraphs.
  - Some options are made explicitly mutually exclusive, such as `annotate`'s
    `--skip-unrecognised` and `--style`, and `download`'s `--output` and
    `--all`.
  - Subcommands which take a list of things (files, license) as arguments, such
    as `annotate`, `lint-file`, or `download`, now also allow zero arguments.
    This will do nothing, but can be useful in scripting.
  - `annotate` and `lint-file` now also take directories as arguments. This will
    do nothing, but can be useful in scripting.

- Changes to comment styles:
  - Allow Python-style comments in Cargo.lock files. (#1060)
  - `.s` files (GNU as) now use the C comment style. (#1034)
  - `.ld` files (GNU ld) now use the C comment style. (#1034)
- `REUSE.toml` no longer needs a licensing header. (#1042)
- `.gitkeep` is no longer ignored, because this is not defined in the
  specification. However, if `.gitkeep` is a 0-size file, it will remain ignored
  (because 0-size files are ignored). (#1043)
- If `REUSE.toml` is ignored by VCS, the linter no longer parses this file.
  (#1047)
- SPDX license and exception list updated to v3.25.0.
- More `LICENSE` and `COPYING`-like files are ignored. Now, such files suffixed
  by `-anything` are also ignored, typically something like `LICENSE-MIT`. Files
  with the UK spelling `LICENCE` are also ignored. (#1041)

### Removed

- Python 3.8 support removed. (#1080)

### Fixed

- In `REUSE.toml`, fixed the globbing of a single asterisk succeeded by a slash
  (e.g. `directory-*/foo.py`). The glob previously did nothing. (#1078)
- Increased the minimum requirement of `attrs` to `>=21.3`. Older versions do
  not import correctly. (#1044)
- Performance greatly improved for projects with large directories ignored by
  VCS. (#1047)
- Performance slightly improved for large projects. (#1047)
- The plain output of `lint` has been slightly improved, getting rid of an
  errant newline. (#1091)
- `reuse annotate --merge-copyrights` now works more reliably with copyright
  prefixes. This still needs some work, though. (#979)
- In some scenarios, where a user has multiple `REUSE.toml` files and one of
  those files could not be parsed, the wrong `REUSE.toml` was signalled as being
  unparseable. This is now fixed. (#1047)
- Fixed a bug where `REUSE.toml` did not correctly apply its annotations to
  files which have an accompanying `.license` file. (#1058)
- When running `reuse download SPDX-IDENTIFIER+`, download `SPDX-IDENTIFIER`
  instead. This also works for `reuse download --all`. (#1098)

## v4.0.3 - 2024-07-08

### Fixed

- Increased the minimum requirement of `attrs` to `>=21.3`. Older versions do
  not import correctly. (#1044)

## v4.0.2 - 2024-07-03

### Fixed

- Repaired a bug that would cause a crash when running
  `annotate --merge-copyrights` on a file that does not yet have a year in the
  copyright statement. This bug was introduced in v4.0.1. (#1030)

## v4.0.1 - 2024-07-03

### Fixed

- Make sure that Read the Docs can compile the documentation. This necesitated
  updating `poetry.lock`. (#1028)

## v4.0.0 - 2024-07-03

This release of REUSE implements the new
[REUSE Specification v3.2](https://reuse.software/spec-3.2). It adds the
`REUSE.toml` file format as a replacement for `.reuse/dep5`. The new format is
easier to write and parse, is better at disambiguating certain corner cases, and
is more flexible for customisation and future additions.

To convert your existing `.reuse/dep5` to `REUSE.toml`, you can simply use the
`reuse convert-dep5` command.

Alongside the `REUSE.toml` feature is a wealth of other improvements.
`reuse lint --lines` may be especially interesting for CI workflows, as well as
the fact that the amount of `PendingDeprecationWarning`s has been drastically
reduced now that the information aggregation behaviour of `.reuse/dep5` is
explicitly defined in the specification.

The tool has also been made easier to use with the addition of man pages. The
man pages can be found online at <https://reuse.readthedocs.io/en/stable/man/>.
Your distribution's packager will need to make them accessible via
`man reuse(1)`. Unfortunately, man pages cannot be made accessible via Python's
packaging, although the full documentation (including man pages) is included in
the sdist.

This changeset also contains the changes of v3.1.0a1.

### Added

- Added support for `REUSE.toml`. (#863)
- Added `reuse convert-dep5` to convert `.reuse/dep5` to `REUSE.toml`. (#863)
- Man pages added for all `reuse` commands. Distribution maintainers might wish
  to distribute the (Sphinx-built) man pages. (#975)
- More file types are recognised:
  - Assembler (`.asm`) (#928)
  - GraphQL (`.graphqls`, `.gqls`) (#930)
  - CUDA-C++ (`.cu`, `.cuh`) (#938)
  - Various .NET files (`.csproj`, `.fsproj`, `.fsx`, `.props`, `.sln`,
    `.vbproj`) (#940)
  - Cargo (`Cargo.lock`) (#937)
  - Clang-Tidy (`.clang-tidy`) (#961)
  - Java `.properties` files (#968)
  - Apache HTTP server config `.htaccess` files (#985)
  - npm `.npmrc` files (#985)
  - LaTeX class files (`.cls`) (#971)
  - CSON (`.cson`) (#1002)
  - Hjson (`.hjson`) (#1002)
  - JSON5 (`.json5`) (#1002)
  - JSON with Comments (`.jsonc`) (#1002)
  - Tap (`.taprc`) (#997)
  - Zsh (`.zshrc`) (#997)
  - Perl test (`.t`) (#997)
  - BATS test (`.bats`) (#997)
  - Octave/Matlab (`.m`) (#604)
  - VHDL(`.vhdl`) (#564)
  - Earthly files (`Earthfile` and `.earthlyignore`) (#1024)
- Added comment styles:
  - `man` for UNIX Man pages (`.man`) (#954)
- Added `--lines` output option for `lint`. (#956)
- Treat `% !TEX` and `% !BIB` as shebangs in TeX and BibTeX files, respectively
  (#971)
- Support alternate spelling `--skip-unrecognized`. (#974)
- In `annotate`, rename `--copyright-style` to `--copyright-prefix`. The former
  parameter is still supported. (#973)
- Support alternate spelling `--skip-unrecognized` (#974)
- `cpp` and `cppsingle` style shorthands (see changes). (#941)

### Changed

- Updated SPDX resources to 3.24.0. (#994)
- Updated REUSE specification version to 3.2. (#994)
- `.s` files now use the Python comment style as per GNU Assembler (gas). (#928)
- Previously, any file that begins with `COPYING` or `LICENSE` was ignored. This
  has been changed. Now, files like `COPYING_README` are no longer ignored, but
  `COPYING` and `COPYING.txt` are still ignored (in other words: exact matches,
  or `COPYING` + a file extension). Idem ditto for `LICENSE`. (#886)
- Dependencies added:
  - `attrs>=21.1` (#863)
  - `tomlkit>=0.8` (#863)
- Reorganised the way that `c`, `css`, and `csingle` styles work. (#941)
  - `c` used to support multi-line comments; it now only supports multi-line
    `/* */` comments. This is identical to the old `css` style.
  - `cpp` has been added, which supports multi-line `/* */` comments and
    single-line `//` comments. This is identical to the old `c` style.
  - `csingle` has been renamed to `cppsingle`, and it supports only single-line
    `//` comments.

### Deprecated

- `.reuse/dep5` is marked deprecated. `reuse convert-dep5` will help you switch
  to `REUSE.toml`. (#863)

### Removed

- The PendingDeprecationWarning for the aggregation of information between DEP5
  and the contents of a file has been removed. This behaviour is now explicitly
  specified in REUSE Specification v3.2. (#1017, related to #779)
- `reuse init` removed. (#863)
- `csingle` and `css` style shorthands (see changes). (#941)

### Fixed

- The datetime value for `Created:` was wrongly formatted since 3.0.0. It now
  returns a correctly formatted ISO 8601 date again. (#952)
- Repaired the behaviour of `reuse download` where being inside of a LICENSES/
  directory should not create a deeper LICENSES/LICENSES/ directory. (#975)
- Support annotating a file that contains only a shebang. (#965)
- Add `CONTRIBUTING.md` to the sdist. (#987)
- In `reuse spdx`, fixed the output to be more compliant by capitalising
  `SPDXRef-Document DESCRIBES` appropriately. (#1013)

## v3.0.2 - 2024-04-08

### Fixed

- `annotate`'s '`--style` now works again when used for a file with an
  unrecognised extension. (#909)

## v3.0.1 - 2024-01-19

### Fixed

- `.qrc` and `.ui` now have the HTML comment style instead of being marked
  uncommentable. (#896)
- This reverts behaviour introduced in v3.0.0: the contents of uncommentable
  files are scanned for REUSE information again. The contents of binary files
  are not. (#896)

## v3.0.0 - 2024-01-17

This release contains a lot of small improvements and changes without anything
big per se. Rather, it is made in advance of a release which will contain a
single feature: [REUSE.toml](https://github.com/fsfe/reuse-tool/issues/779), a
replacement for `.reuse/dep5`. `.reuse/dep5` will still be supported as a
deprecated feature for some time.

That future 3.1 release will have some alpha testing in advance.

### Added

- Implement handling LicenseRef in `download` and `init`. (#697)
- Declared support for Python 3.12. (#846)
- More file types are recognised:
  - TCL (`.tcl`) (#871)
  - Julia (`.jl`) (#815)
  - Modern Fortran (`.f90`) (#836)
  - Bazel (`.bzl`) (#870)
  - GNU Linker script (`.ld`) (#862)
  - Assembly code (`.s`) (#862)
  - Empty placeholders (`.empty`) (#862)
  - ShellCheck configuration (`.shellcheckrc`) (#862)
  - Pylint in-project configuration (`pylintrc`) (#862)
  - Lisp schemes (`.sld`, `.sls`, `.sps`) (#875)
- Added comment styles:
  - `csingle` for Zig (`.zig`) and Hare (`.ha`) (#889)
- Display recommendations for steps to fix found issues during a lint. (#698)
- Add support for Pijul VCS. Pijul support is not added to the Docker image.
  (#858)
- When running `annotate` on a file with an unrecognised file path, the tool
  currently exits early. To automatically create a .license file for
  unrecognised files, `--fallback-dot-license` has been added. (#823, #851,
  #853, #859; this took a while to get right.)
- Ignore `.sl` directory as used by [Sapling SCM](https://sapling-scm.com/).
  (#867)

### Changed

- Alpine Docker image now uses 3.18 as base. (#846)
- The Git submodule detection was made less naïve. Where previously it detected
  a directory with a `.git` file as a submodule, it now uses the git command to
  detect submodules. This helps detect (quoted from Git man page)
  "[repositories] that were cloned independently and later added as a submodule
  or old setups", which "have the submodule's git directory inside the submodule
  instead of embedded into the superproject's git directory". (#687)
- No longer scan binary or uncommentable files for their contents in search of
  REUSE information. (#825)
- `--force-dot-license` and `--skip-unrecognised` are now mutually exclusive on
  `annotate`. (#852)
- No longer create and publish `-extra` Docker images. The `openssh-client`
  package is now in the main image. (#849)
- No longer create and publish `dev` Docker images. (#849)
- The `-debian` Docker image is now based off debian:12-slim. It used to be
  based on the python:slim image, which used debian:slim under the hood. (#849)

### Removed

- Removed deprecated `--explicit-license`. (#851)
- Removed deprecated `addheader`. (#851)
- No longer depend on `sphinx-autodoc-typehints` for documentation. (#772)

### Fixed

- Syntax errors in .reuse/dep5 now have better error handling. (#841)
- Reduced python-debian minimum version to 0.1.34. (#808)
- Fix issue in `annotate` where `--single-line` and `--multi-line` would not
  correctly raise an error with an incompatible comment style. (#853)
- Fix parsing existing copyright lines when they do not have a year (#861)
- Better handling of Lisp comment styles. Now, any number of ";" characters is
  recognised as the prefix to a Lisp comment, and ";;;" is used when inserting
  comment headers, as per
  <https://www.gnu.org/software/emacs/manual/html_node/elisp/Comment-Tips.html>.
  (#874)

## v2.1.0 - 2023-07-18

After the yanked 2.0.0 release, we're excited to announce our latest major
version packed with new features and improvements! We've expanded our file type
recognition, now including Fennel, CommonJS, Qt .pro, .pri, .qrc, .qss, .ui,
Textile, Visual Studio Code workspace, Application Resource Bundle, Svelte
components, AES encrypted files, Jakarta Server Page, Clang format, Browserslist
config, Prettier config and ignored files, Flutter pubspec.lock, .metadata,
Terraform and HCL, Typst and more.

We've also added the ability to detect SPDX snippet tags in files and introduced
additional license metadata for the Python package. A new `--json` flag has been
added to the `lint` command, marking the first step towards better integration
of REUSE output with other tools.

On the changes front, we've bumped the SPDX license list to v3.21 and made
significant updates to our Sphinx documentation. Please note that Python 3.6 and
3.7 support has been dropped in this release.

We've fixed several issues including automatic generation of Sphinx
documentation via readthedocs.io and a compatibility issue where reuse could not
be installed if gettext is not installed.

This update is all about making your experience better. Enjoy adding copyright
and licensing information to your code!

### Added

- Detect SPDX snippet tags in files. (#699)
- More file types are recognised:
  - Fennel (`.fnl`) (#638)
  - CommonJS (`.cjs`) (#632)
  - Qt .pro (`.pro`) (#632)
  - Qt .pri (`.pri`) (#755)
  - Qt .qrc (`.qrc`) (#755)
  - Qt .qss(`.qss`) (#755)
  - Qt .ui (`.ui`) (#755)
  - Textile (`.textile`) (#712)
  - Visual Studio Code workspace (`.code-workspace`) (#747)
  - Application Resource Bundle (`.arb`) (#749)
  - Svelte components (`.svelte`)
  - AES encrypted files (`.aes`) (#758)
  - Jakarte Server Page (`.jsp`) (#757)
  - Clang format (`.clang-format`) (#632)
  - Browserslist config (`.browserslist`)
  - Prettier config (`.prettierrc`) and ignored files (`.prettierignore`)
  - Flutter pubspec.lock (`pubspec.lock`) (#751)
  - Flutter .metadata (`.metadata`) (#751)
  - Terraform (`.tf`, `tfvars`) and HCL (`.hcl`). (#756)
  - Typst (`.typ`)
- Added loglevel argument to pytest and skip one test if loglevel is too high
  (#645).
- `--add-license-concluded`, `--creator-person`, and `--creator-organization`
  added to `reuse spdx`. (#623)
- Additional license metadata for the Python package has been added. The actual
  SPDX license expression remains the same:
  `Apache-2.0 AND CC0-1.0 AND CC-BY-SA-4.0 AND GPL-3.0-or-later`. (#733)
- Added `--contributor` option to `annotate`. (#669)
- Added `--json` flag to `lint` command (#654).
- `reuse.ReuseInfo` now has `copy` and `union` methods. (#759)
- `reuse.ReuseInfo` now stores information about the source from which the
  information was gathered. (#654, #787)
- Added Ukrainian and Czech translations (#767)
- Added `--suppress-deprecation` to hide (verbose) deprecation warnings. (#778)

### Changed

- Bumped SPDX license list to v3.20. (#692)
- `reuse.SpdxInfo` was renamed to `reuse.ReuseInfo`. It is now a (frozen)
  dataclass instead of a namedtuple. This is only relevant if you're using reuse
  as a library in Python. Other functions and methods were similarly renamed.
  (#669)
- Sphinx documentation: Switched from RTD theme to Furo. (#673, #716)
- Removed dependency on setuptools' `pkg_resources` to determine the installed
  version of reuse. (#724)
- Bumped SPDX license list to v3.21. (#763)
- `Project.reuse_info_of` now returns a list of `ReuseInfo` objects instead of a
  single one. This is because the source information is now stored alongside the
  REUSE information. (#787)

### Deprecated

- Pending deprecation of aggregation of file sources. Presently, when copyright
  and licensing information is defined both within e.g. the file itself and in
  the DEP5 file, then the information is merged or aggregated for the purposes
  of linting and BOM generation. In the future, this will no longer be the case
  unless explicitly defined. The exact mechanism for this is not yet concrete,
  but a `PendingDeprecationWarning` will be shown to the user to make them aware
  of this. (#778)

### Removed

- Python 3.6 and 3.7 support has been dropped. (#673, #759)
- Removed runtime and build time dependency on `setuptools`. (#724)

### Fixed

- Fixed automatic generation of Sphinx documentation via readthedocs.io by
  adding a `.readthedocs.yaml` configuration file (#648)
- Fixed a compatibility issue where reuse could not be installed (built) if
  gettext is not installed. (#691)
- Translations are available in Docker images. (#701)
- Marked the `/data` directory in Docker containers as safe in Git, preventing
  errors related to linting Git repositories. (#720)
- Repaired error when using Galician translations. (#719)

### Security

## v2.0.0 - 2023-06-21 [YANKED]

This version was yanked because of an unanticipated workflow that we broke. The
breaking change is the fact that an order of precedence was defined for
copyright and licensing information sources. For instance, if a file contained
the `SPDX-License-Identifier` tag, and if that file was also (explicitly or
implicitly) covered by DEP5, then the information from the DEP5 setting would no
longer apply to that file.

While the intention of the breaking change was sound (don't mix information
sources; define a single source of truth), there were legitimate use-cases that
were broken as a result of this.

Apologies to everyone whose CI broke. We'll get this one right before long.

## v1.1.2 - 2023-02-09

### Fixed

- Note to maintainers: It is now possible/easier to use the `build` module to
  build this module. Previously, there was a namespace conflict. (#640)

## v1.1.1 - 2023-02-05

### Fixed

- Don't include documentation files (e.g. `README.md`) in top-level (i.e.,
  `site-packages/`). (#657)
- Include documentation directory in sdist. (#657)

## v1.1.0 - 2022-12-01

### Added

- Added support for Python 3.11. (#603)
- More file types are recognised:
  - Kotlin script (`.kts`)
  - Android Interface Definition Language (`.aidl`)
  - Certificate files (`.pem`)
- Added comment styles:
  - Apache Velocity Template (Extensions: `.vm`, `.vtl`) (#554)
  - XQuery comment style (Extensions: `.xq(l|m|y|uery|)`) (#610)
- Some special endings are always stripped from copyright and licensing
  statements (#602):
  - `">` (and variations such as `'>`, `" >`, and `"/>`)
  - `] ::`

### Changed

- Removed `setup.py` and replaced it with a Poetry configuration. Maintainers
  beware. (#600)
- Updated PyPI development status to 'production/stable' (#381)
- The pre-commit hook now passes `lint` as an overridable argument. (#574)
- `addheader` has been renamed to `annotate`. The functionality remains the
  same. (#550)
- Bumped SPDX license list to v3.19.

### Deprecated

- `addheader` has been deprecated. It still works, but is now undocumented.
  (#550)

### Removed

- `setup.py`. (#600)
- Releases to PyPI are no longer GPG-signed. Support for this is not present in
  Poetry and not planned. (#600)
- Dependency on `requests` removed; using `urllib.request` from the standard
  library instead. (#600)

### Fixed

- Repair tests related to CVE-2022-39253 changes in upstream Git. New versions
  of Git no longer allow `git submodule add repository path` where repository is
  a file. A flag was added to explicitly allow this in the test framework.
  (#619)
- Sanitize xargs input in scripts documentation. (#525)
- License identifiers in comments with symmetrical ASCII art frames are now
  properly detected (#560)
- Fixed an error where copyright statements contained within a multi-line
  comment style on a single line could not be parsed (#593).
- In PHP files, add header after `<?php` (#543).

## v1.0.0 - 2022-05-19

A major release! Do not worry, no breaking changes but a development team
(@carmenbianca, @floriansnow, @linozen, @mxmehl and @nicorikken) that is
confident enough to declare the REUSE helper tool stable, and a bunch of
long-awaited features!

Apart from smaller changes under the hood and typical maintenance tasks, the
main additions are new flags to the `addheader` subcommand that ease recursive
and automatic operations, the ability to ignore areas of a file that contain
strings that may falsely be detected as copyright or license statements, and the
option to merge copyright lines. The tool now also has better handling of some
edge cases with copyright and license identifiers.

We would like to thank the many contributors to this release, among them
@ajinkyapatil8190, @aspiers, @ferdnyc, @Gri-ffin, @hexagonrecursion, @hoijui,
@Jakelyst, @Liambeguin, @rex4539, @robinkrahl, @rpavlik, @siiptuo, @thbde and
@ventosus.

### Added

- Extend [tool documentation](https://reuse.readthedocs.io) with scripts to help
  using this tool and automating some steps that are not built into the tool
  itself. (#500)
- Recommendations for installation/run methods: package managers and pipx (#457)
- Docker images for AArch64 (#478)
- Added the ability to ignore parts of a file when running `reuse lint`. Simply
  add `REUSE-IgnoreStart` and `REUSE-IgnoreEnd` as comments and all lines
  between the two will be ignored by the next run of `reuse lint`. (#463)
- [Meson subprojects](https://mesonbuild.com/Subprojects.html) are now ignored
  by default. (#496)
- More file types are recognised:
  - sbt build files (`.sbt`)
  - Vimscript files (`.vim`)
- Added `--skip-existing` flag to `addheader` in order to skip files that
  already contain SPDX information. This may be useful for only adding SPDX
  information to newly created files. (#480)
- Added `--recursive` flag to `addheader`. (#469)
- Preserve shebang for more script files:
  - V-Lang (#432)
- Ignore all SPDX files with their typical formats and extensions. (#494)
- Add support for merging copyright lines based on copyright statement,
  transforming multiple lines with a single year into a single line with a
  range. (#328)

### Changed

- Use `setuptools` instead of the deprecated `distutils` which will be removed
  with Python 3.12. (#451)
- `addheader --explicit-license` renamed to `--force-dot-license`. (#476)
- Dockerfiles for reuse-tool are now in a separate subdirectory `docker`. (#499)
- Updated SPDX license list to 3.17. (#513)
- The copyright detection mechanism now silently accepts the following strings:
  `Copyright(c)` and `Copyright(C)`. (#440)

### Deprecated

- Deprecated `--explicit-license` in favour of `--force-dot-license`.
  `--explicit-license` will remain useable (although undocumented) for the
  foreseeable future. (#476)

### Removed

- `JsxCommentStyle` in favor of using `CCommentStyle` directly (see section
  `Fixed`). (#406)

### Fixed

- Better support for unary "+" operator in license identifiers. For example, if
  `Apache-1.0+` appears as a declared license, it should not be identified as
  missing, bad, or unused if `LICENSES/Apache-1.0.txt` exists. It is, however,
  identified separately as a used license. (#123)
- When `addheader` creates a `.license` file, that file now has a newline at the
  end. (#477)
- Cleaned up internal string manipulation. (#477)
- JSX (`.jxs` and `.tsx`) actually uses C comment syntax as JSX blocks never
  stand at the beginning of the file where the licensing info needs to go.
  (#406)

## v0.14.0 - 2021-12-27

Happy holidays! This is mainly a maintenance release fixing some subcommands and
adding loads of supported file types and file names. However, you can also enjoy
the `supported-licenses` subcommand and the `--quiet` flag for linting as well
as better suggestions for license identifiers. Thanks to everyone who
contributed!

### Added

- `supported-licenses` command that lists all licenses supported by REUSE (#401)
- `--quiet` switch to the `lint` command (#402)
- Better suggestions for faulty SPDX license identifiers in `download` and
  `init` (#416)
- Python 3.10 support declared
- More file types are recognised:
  - Apache FreeMarker Template Language (`.ftl`)
  - AsciiDoc (`.adoc`, `.asc`, `.asciidoc`)
  - Bibliography (`.csl`)
  - C++ (`.cc` and `.hh`)
  - GraphQL (`.graphql`)
  - Handlebars (`.hbs`)
  - Markdown-linter config (`.mdlrc`)
  - MS Office (`.doc`, `.xls`, `.pptx` and many more)
  - Nimble (`.nim.cfg`, `.nimble`)
  - Open Document Format (`.odt`, `.ods`, `.fodp` and many more)
  - Perl plain old documentation (`.pod`)
  - Portable document format (`.pdf`)
  - Protobuf files (`.proto`)
  - Soy templates (`.soy`)
  - SuperCollider (`.sc`, `.scsyndef`)
  - Turtle/RDF (`.ttl`)
  - V-Lang (`.v`, `.vsh`)
  - Vue.js (`.vue`)
- More file names are recognised:
  - Doxygen (`Doxyfile`)
  - ESLint (`.eslintignore` and `.eslintrc`)
  - Meson options file (`meson_options.txt`)
  - NPM ignore (`.npmignore`)
  - Podman container files (`Containerfile`)
  - SuperCollider (`archive.sctxar`)
  - Yarn package manager (`.yarn.lock` and `.yarnrc`)

### Changed

- Updated SPDX license list to 3.15

### Fixed

- Fix Extensible Stylesheet Language (`.xsl`) to use HTML comment syntax
- Allow creating .license file for write-protected files (#347) (#418)
- Do not break XML files special first line (#378)
- Make `download` subcommand work correctly outside of project root and with
  `--root` (#430)

## v0.13.0 - 2021-06-11

### Added

- `addheader` recognises file types that specifically require .license files
  instead of headers using `UncommentableCommentStyle`. (#189)
- `.hgtags` is ignored. (#227)
- `spdx-symbol` added to possible copyright styles. (#350)
- `addheader` ignores case when matching file extensions and names. (#359)
- Provide `latest-debian` as Docker Hub tag, created by `Dockerfile-debian`.
  (#321)
- More file types are recognised:
  - Javascript modules (`.mjs`)
  - Jupyter Notebook (`.ipynb`)
  - Scalable Vector Graphics (`.svg`)
  - JSON (`.json`)
  - Comma-separated values (`.csv`)
  - Racket (`.rkt`)
  - Org-mode (`.org`)
  - LaTeX package files (`.sty`)
  - devicetree (`.dts`, `.dtsi`)
  - Bitbake (.bb, .bbappend, .bbclass)
  - XML schemas (`.xsd`)
  - OpenSCAD (`.scad`)
- More file names are recognised:
  - Bash configuration (`.bashrc`)
  - Coverage.py (`.coveragerc`)
  - Jenkins (`Jenkinsfile`)
  - SonarScanner (`sonar-project.properties`)
  - Gradle (`gradle-wrapper.properties`, `gradlew`)

### Changed

- Bump `alpine` Docker base image to 3.13. (#369)

### Fixed

- Fixed a regression where unused licenses were not at all detected. (#285)
- Declared dependency on `python-debian != 0.1.39` on Windows. This version does
  not import on Windows. (#310)
- `MANIFEST.in` is now recognised instead of the incorrect `Manifest.in` by
  `addheader`. (#306)
- `addheader` now checks whether a file is both readable and writeable instead
  of only writeable. (#241)
- `addheader` now preserves line endings. (#308)
- `download` does no longer fail when both `--output` and `--all` are used.
  (#326)
- Catch erroneous SPDX expressions. (#331)
- Updated SPDX license list to 3.13.

## v0.12.1 - 2020-12-17

### Fixed

- Bumped versions of requirements. (#288)

## v0.12.0 - 2020-12-16

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
  - ClojureScript (`.cljc`, `.cljs`)
  - Fortran (`.F`, `.F90`, `.f90`, `.f95`, `.f03`, `.f`, `.for`)
  - Makefile (`.mk`)
  - PlantUML (`.iuml`, `.plantuml`, `.pu`, `.puml`)
  - R (`.R`, `.Renviron`, `.Rprofile`)
  - ReStructured Text (`.rst`)
  - RMarkdown (`.Rmd`)
  - Scheme (`.scm`)
  - TypeScript (`.ts`)
  - TypeScript JSX (`.tsx`)
  - Windows Batch (`.bat`)
- More file names are recognised:
  - .dockerignore
  - Gemfile
  - go.mod
  - meson.build
  - Rakefile

### Changed

- Use UTF-8 explicitly when reading files (#242)

### Fixed

- Updated license list to 3.11.

## v0.11.1 - 2020-06-08

### Fixed

- Similar to CAL-1.0 and CAL-1.0-Combined-Work-Exception, SHL-2.1 is now ignored
  because it contains an SPDX tag within itself.

## v0.11.0 - 2020-05-25

### Added

- Added `--skip-unrecognised` flag to `addheader` in order to skip files with
  unrecognised comment styles instead of aborting without processing any file.

### Changed

- Always write the output files encoded in UTF-8, explicitly. This is already
  the default on most Unix systems, but it was not on Windows.
- All symlinks and 0-sized files in projects are now ignored.

### Fixed

- The licenses CAL-1.0 and CAL-1.0-Combined-Work-Exception contain an SPDX tag
  within themselves. Files that are named after these licenses are now ignored.
- Fixed a bug where `addheader` wouldn't properly apply the template on
  `.license` files if the `.license` file was non-empty, but did not contain
  valid SPDX tags.

## v0.10.1 - 2020-05-14

### Fixed

- Updated license list to 3.8-106-g4cfec76.

## v0.10.0 - 2020-04-24

### Added

- Add support for autoconf comment style (listed as m4).
- More file types are recognised:
  - Cython (`.pyx`, `.pxd`)
  - Sass and SCSS (`.sass`, `.scss`)
  - XSL (`.xsl`)
  - Mailmap (`.mailmap`)
- Added `--single-line` and `--multi-line` flags to `addheader`. These flags
  force a certain comment style.

### Changed

- The Docker image has an entrypoint now. In effect, this means running:
  `docker run -v $(pwd):/data fsfe/reuse lint` instead of
  `docker run -v $(pwd):/data fsfe/reuse reuse lint`.

## v0.9.0 - 2020-04-21

### Added

- Added support for Mercurial 4.3+.
- A pre-commit hook has been added.
- When an incorrect SPDX identifier is forwarded to `download` or `init`, the
  tool now suggests what you might have meant.

### Changed

- Under the hood, a lot of code that has to do with Git and Mercurial was moved
  into its own module.
- The Docker image has been changed such that it now automagically runs
  `reuse lint` on the `/data` directory unless something else is specified by
  the user.

### Fixed

- Fixed a bug with `addheader --explicit-license` that would result in
  `file.license.license` if `file.license` already existed.
- Fixed a Windows-only bug to do with calling subprocesses.
- Fixed a rare bug that would trigger when a directory is both ignored and
  contains a `.git` file.

## v0.8.1 - 2020-02-22

### Added

- Support Jinja (Jinja2) comment style.
- Support all multi-line comment endings when parsing for SPDX information.

### Fixed

- Improvements to German translation by Thomas Doczkal.
- No longer remove newlines at the end of files when using `addheader`.
- There can now be a tab as whitespace after `SPDX-License-Identifier` and
  `SPDX-FileCopyrightText`.

## v0.8.0 - 2020-01-20

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
  - Dutch (André Ockers, Carmen Bianca Bakker)
  - French (OliBug, Vincent Lequertier)
  - Galician (pd)
  - German (Max Mehl)
  - Esperanto (Carmen Bianca Bakker)
  - Portuguese (José Vieira)
  - Spanish (Roberto Bauglir)
  - Turkish (T. E. Kalayci)

### Changed

- The linter output has been very slightly re-ordered to be more internally
  consistent.
- `reuse --version` now prints a version with a Git hash on development
  versions. Towards that end, the tool now depends on `setuptools-scm` during
  setup. It is not a runtime dependency.

### Removed

- `lint` no longer accepts path arguments. Where previously one could do
  `reuse lint SUBDIRECTORY`, this is no longer possible. When linting, you must
  always lint the entire project. To change the project's root, use `--root`.
- `FileReportInfo` has been removed. `FileReport` is used instead.

### Fixed

- A license that does not have a file extension, but whose full name is a valid
  SPDX License Identifier, is now correctly identified as such. The linter will
  complain about them, however.
- If the linter detects a license as being a bad license, that license can now
  also be detected as being missing.
- Performance of `project.all_files()` has been improved by quite a lot.
- Files with CRLF line endings are now better supported.

## v0.7.0 - 2019-11-28

### Changed

- The program's package name on PyPI has been changed from `fsfe-reuse` to
  `reuse`. `fsfe-reuse==1.0.0` has been created as an alias that depends on
  `reuse`. `fsfe-reuse` will not receive any more updates, but will still host
  the old versions.
- For users of `fsfe-reuse`, this means:
  - If you depend on `fsfe-reuse` or `fsfe-reuse>=0.X.Y` in your
    requirements.txt, you will get the latest version of `reuse` when you
    install `fsfe-reuse`. You may like to change the name to `reuse` explicitly,
    but this is not strictly necessary.
  - If you depend on `fsfe-reuse==0.X.Y`, then you will keep getting that
    version. When you bump the version you depend on, you will need to change
    the name to `reuse`.
  - If you depend on `fsfe-reuse>=0.X.Y<1.0.0`, then 0.6.0 will be the latest
    version you receive. In order to get a later version, you will need to
    change the name to `reuse`.

## v0.6.0 - 2019-11-19

### Added

- `--include-submodules` is added to also include submodules when linting et
  cetera.
- `addheader` now also recognises the following extensions:
  - .kt
  - .xml
  - .yaml
  - .yml

### Changed

- Made the workaround for `MachineReadableFormatError` introduced in 0.5.2 more
  generic.
- Improved shebang detection in `addheader`.
- For `addheader`, the SPDX comment block now need not be the first thing in the
  file. It will find the SPDX comment block and deal with it in-place.
- Git submodules are now ignored by default.
- `addheader --explicit-license` now no longer breaks on unsupported filetypes.

## v0.5.2 - 2019-10-27

### Added

- `python3 -m reuse` now works.

### Changed

- Updated license list to 3.6-2-g2a14810.

### Fixed

- Performance of `reuse lint` improved by at least a factor of 2. It no longer
  does any checksums on files behind the scenes.
- Also handle `MachineReadableFormatError` when parsing DEP5 files. Tries to
  import that error. If the import is unsuccessful, it is handled.

## v0.5.1 - 2019-10-24 [YANKED]

This release was replaced by 0.5.2 due to importing
`MachineReadableFormatError`, which is not a backwards-compatible change.

## v0.5.0 - 2019-08-29

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

## v0.4.1 - 2019-08-07

### Added

- `--all` argument help to `reuse download`, which downloads all detected
  missing licenses.

### Fixed

- When using `reuse addheader` on a file that contains a shebang, the shebang is
  preserved.
- Copyright lines in `reuse spdx` are now sorted.
- Some publicly visible TODOs were patched away.

## v0.4.0 - 2019-08-07

This release is a major overhaul and refactoring of the tool. Its primary focus
is improved usability and speed, as well as adhering to version 3.0 of the REUSE
Specification.

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
- In addition to `Copyright` and `©`, copyright lines can be marked with the
  tag `SPDX-FileCopyrightText:`. This is the new recommended default.
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

## v0.3.4 - 2019-04-15

This release should be a short-lived one. A new (slightly
backwards-incompatible) version is in the works.

### Added

- Copyrights can now start with `©` in addition to `Copyright`. The former is
  now recommended, but they are functionally similar.

### Changed

- The source code of reuse is now formatted with black.
- The repository has been moved from <https://git.fsfe.org/reuse/reuse> to
  <https://gitlab.com/reuse/reuse>.

## v0.3.3 - 2018-07-15

### Fixed

- Any files with the suffix `.spdx` are no longer considered licenses.

## v0.3.2 - 2018-07-15

### Fixed

- The documentation now builds under Python 3.7.

## v0.3.1 - 2018-07-14

### Fixed

- When using reuse from a child directory using pygit2, correctly find the root.

## v0.3.0 - 2018-05-16

### Changed

- The output of `reuse compile` is now deterministic. The files, copyright lines
  and SPDX expressions are sorted alphabetically.

### Fixed

- When a GPL license could not be found, the correct `-only` or `-or-later`
  extension is now used in the warning message, rather than a bare `GPL-3.0`.
- If you have a license listed as `SPDX-Valid-License: GPL-3.0-or-later`, this
  now correctly matches corresponding SPDX identifiers. Still it is recommended
  to use `SPDX-Valid-License: GPL-3.0` instead.

## v0.2.0 - 2018-04-17

### Added

- Internationalisation support added. Initial support for:
  - English.
  - Dutch.
  - Esperanto.
  - Spanish.

### Fixed

- The license list of SPDX 3.0 has deprecated `GPL-3.0` and `GPL-3.0+` et al in
  favour of `GPL-3.0-only` and `GPL-3.0-or-later`. The program has been amended
  to accommodate sufficiently for those licenses.

### Changed

- `Project.reuse_info_of` now extracts, combines and returns information both
  from the file itself and from debian/copyright.
- `ReuseInfo` now holds sets instead of lists.
  - As a result of this, `ReuseInfo` will not hold duplicates of copyright lines
    or SPDX expressions.
- click removed as dependency. Good old argparse from the library is used
  instead.

## v0.1.1 - 2017-12-14

### Changed

- The `reuse --help` text has been tidied up a little bit.

### Fixed

- Release date in change log fixed.
- The PyPI homepage now gets reStructuredText instead of Markdown.

## v0.1.0 - 2017-12-14

### Added

- Successfully parse old-style C and HTML comments now.
- Added `reuse compile`, which creates an SPDX bill of materials.
- Added `--ignore-missing` to `reuse lint`.
- Allow to specify multiple paths to `reuse lint`.
- `chardet` added as dependency.
- `pygit2` added as soft dependency. reuse remains usable without it, but the
  performance with `pygit2` is significantly better. Because `pygit2` has a
  non-Python dependency (`libgit2`), it must be installed independently by the
  user. In the future, when reuse is packaged natively, this will not be an
  issue.

### Changed

- Updated to version 2.0 of the REUSE recommendations. The most important change
  is that `License-Filename` is no longer used. Instead, the filename is
  deducted from `SPDX-License-Identifier`. This change is **NOT** backwards
  compatible.
- The conditions for linting have changed. A file is now non-compliant when:
  - The license associated with the file could not be found.
  - There is no SPDX expression associated with the file.
  - There is no copyright notice associated with the file.
- Only read the first 4 KiB (by default) from code files rather than the entire
  file when searching for SPDX tags. This speeds up the tool a bit.
- `Project.reuse_info_of` no longer raises an exception. Instead, it returns an
  empty `ReuseInfo` object when no reuse information is found.
- Logging is a lot prettier now. Only output entries from the `reuse` module.

### Fixed

- `reuse --ignore-debian compile` now works as expected.
- The tool no longer breaks when reading a file that has a non-UTF-8 encoding.
  Instead, `chardet` is used to detect the encoding before reading the file. If
  a file still has errors during decoding, those errors are silently ignored and
  replaced.

## v0.0.4 - 2017-11-06

### Fixed

- Removed dependency on `os.PathLike` so that Python 3.5 is actually supported

## v0.0.3 - 2017-11-06

### Fixed

- Fixed the link to PyPI in the README.

## v0.0.2 - 2017-11-03

This is a very early development release aimed at distributing the program as
soon as possible. Because this is the first release, the changelog is a little
empty beyond "created the program".

The program can do roughly the following:

- Detect the license of a given file through one of three methods (in order of
  precedence):
  - Information embedded in the .license file.
  - Information embedded in its header.
  - Information from the global debian/copyright file.
- Find and report all files in a project tree of which the license could not be
  found.
- Ignore files ignored by Git.
- Do some logging into STDERR.
