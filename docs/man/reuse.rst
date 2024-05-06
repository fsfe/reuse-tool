..
  SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
  SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>

  SPDX-License-Identifier: CC-BY-SA-4.0

reuse
=====

Synopsis
--------

**reuse** [*options*] <command>

Description
-----------

:program:`reuse` is a helper tool for the REUSE initiative. Its main
functionality in :manpage:`reuse-lint(1)` is to verify whether a project is
compliant with the REUSE Specification. It also contains an array of convenience
functions to enable developers to become compliant.

For more information on how to use reuse beyond a reference of the command-line
options, see the accompanying documentation or read it at
`<https://reuse.readthedocs.io>`_. For further information about REUSE, see
`<https://reuse.software>`_.

Details
-------

When searching for copyright and licensing tags inside of files, the tool does
not strictly limit itself to the header comment as prescribed by the
specification. It searches the first 4 kibibytes of the file for REUSE
information, whether in comments or not. This makes sure that the tool can parse
any type of plain-text file, even if the comment style is not recognised.

If a file is found to have an unparsable tag, that file is not parsed at all.
This is a bug (`<https://github.com/fsfe/reuse-tool/issues/4>`_).

The tool does not verify the correctness of copyright notices. If it finds any
line containing '©', 'Copyright', or 'SPDX-FileCopyrightText:', then the tag and
everything following it is considered a valid copyright notice, even if the
copyright notice is not compliant with the specification.

Symbolic links and files that are zero-sized are automatically ignored.

Options
-------

.. option:: --debug

  Enable debug logging.

.. option:: --suppress-deprecation

  Hide deprecation warnings.

.. option:: --include-submodules

  Do not ignore Git submodules; they are treated as though they are part of the
  project. This is not strictly compliant with the specification.

.. option:: --include-meson-subprojects

  Do not ignore Meson subprojects (i.e. the ``subprojects`` directory in the
  root of the project); they are treated as though they are part of the project.
  This is not strictly compliant with the specification.

.. option:: --no-multiprocessing

  Disable multiprocessing performance enhancer. This may be useful when
  debugging.

.. option:: --root PATH

  Set the root of the project to PATH. Normally this defaults to the root of the
  current working directory's VCS repository, or to the current working
  directory.

.. option:: -h, --help

  Display help and exit. If no command is provided, this option is implied.

.. option:: --version

  Display the version and exit.

Commands
--------

:manpage:`reuse-annotate(1)`
  Add REUSE information to files.

:manpage:`reuse-convert-dep5(1)`
  Convert ``.reuse/dep5`` to ``REUSE.toml``.

:manpage:`reuse-download(1)`
  Download license files.

:manpage:`reuse-lint(1)`
  Verify whether a project is compliant with the REUSE Specification.

:manpage:`reuse-spdx(1)`
  Generate SPDX bill of materials.

:manpage:`reuse-supported-licenses(1)`
  Print a list of supported licenses.
