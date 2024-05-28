..
  SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
  SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>

  SPDX-License-Identifier: CC-BY-SA-4.0

reuse-lint
==========

Synopsis
--------

**reuse lint** [*options*]

Description
-----------

:program:`reuse-lint` verifies whether a project is compliant with the REUSE
Specification located at `<https://reuse.software/spec>`_.

Criteria
--------

These are the criteria that the linter checks against.

Bad licenses
~~~~~~~~~~~~

Licenses that are found in ``LICENSES/`` that are not found in the SPDX License
List or do not start with ``LicenseRef-`` are bad licenses.

Deprecated licenses
~~~~~~~~~~~~~~~~~~~

Licenses whose SPDX License Identifier has been deprecated by SPDX.

Licenses without file extension
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These are licenses whose file names are a valid SPDX License Identifier, but
which do not have a file extension.

Missing licenses
~~~~~~~~~~~~~~~~

A license which is referred to in a comment header, but which is not found in
the ``LICENSES/`` directory.

Unused licenses
~~~~~~~~~~~~~~~

A license found in the ``LICENSES/`` directory, but which is not referred to in
any comment header.

Read errors
~~~~~~~~~~~

Not technically a criterion, but files that cannot be read by the operating
system are read errors, and need to be fixed.

Files without copyright and license information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every file needs to have copyright and licensing information associated with it.
The REUSE Specification details several ways of doing it. By and large, these
are the methods:

- Placing tags in the header of the file.
- Placing tags in a ``.license`` file adjacent to the file.
- Putting the information in the ``REUSE.toml`` file.
- Putting the information in the ``.reuse/dep5`` file. (Deprecated)

If a file is found that does not have copyright and/or license information
associated with it, then the project is not compliant.

Options
-------

.. option:: -q, --quiet

  Do not print anything to STDOUT.

..
  TODO: specify the JSON output.

.. option:: -j, --json

  Output the results of the lint as JSON.

.. option:: -p, --plain

  Output the results of the lint as descriptive text. The text is valid
  Markdown.

.. option:: -l, --lines

  Output one line per error, prefixed by the file path.

.. option:: -h, --help

  Display help and exit.
