..
  SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
  SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>

  SPDX-License-Identifier: CC-BY-SA-4.0

reuse-lint-file
===============

Synopsis
--------

**reuse lint-file** [*options*] [*file* ...]

Description
-----------

:program:`reuse-lint-file` verifies whether the specified files are compliant
with the REUSE Specification located at `<https://reuse.software/spec>`_. It
runs the linter from :manpage:`reuse-lint(1)` against a subset of files, using a
subset of criteria.

Files that are ignored by :program:`reuse-lint` are also ignored by
:program:`reuse-lint-file`, even if specified.

Criteria
--------

The criteria are the same as used in :manpage:`reuse-lint(1)`, but using only a
subset:

- Missing licenses.
- Read errors.
- Files without copyright and license information.

Options
-------

.. option:: -q, --quiet

  Do not print anything to STDOUT.

.. option:: -l, --lines

  Output one line per error, prefixed by the file path. This option is the
  default.

.. option:: --help

  Display help and exit.
