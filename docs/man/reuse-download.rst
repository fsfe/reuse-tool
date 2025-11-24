..
  SPDX-FileCopyrightText: 2024 Free Software Foundation Europe e.V. <https://fsfe.org>

  SPDX-License-Identifier: CC-BY-SA-4.0

reuse-download
==============

Synopsis
--------

**reuse download** [*options*] [*license* ...]

Description
-----------

:program:`reuse-download` downloads licenses into your ``LICENSES/`` directory.

The *license* arguments should be SPDX License Identifiers. If an argument
instead starts with ``LicenseRef-``, then an empty file will be created in the
``LICENSES/`` directory.

The ``LICENSES/`` directory will be found in the root of your project. If you
are already in a directory named ``LICENSES`` and you are not in a VCS
repository, that directory will be used.

If no ``LICENSES/`` directory exists, one will be created.

Options
-------

.. option:: --all

  Download all licenses detected missing in the project.

.. option:: -o, --output FILE

  If downloading a single file, output it to a specific file instead of putting
  it in a detected ``LICENSES/`` directory.

.. option:: --source PATH

  Specify a source from which to copy files. This can be a directory containing
  such files, or a path to the file itself. If a directory is specified, it must
  contain a file named ``<license>.txt`` or ``<license>``, where ``<license>``
  equals the license being downloaded.

  This option also works with licenses that start with ``LicenseRef-``.

.. option:: --help

  Display help and exit.
