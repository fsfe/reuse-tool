..
  SPDX-FileCopyrightText: 2024 Free Software Foundation Europe e.V. <https://fsfe.org>
  SPDX-FileCopyrightText: 2025 Shun Sakai <sorairolake@protonmail.ch>

  SPDX-License-Identifier: CC-BY-SA-4.0

reuse-supported-licenses
========================

Synopsis
--------

**reuse supported-licenses** [*options*]

Description
-----------

:program:`reuse-supported-licenses` generates a list of supported licenses.
These are the licenses in the SPDX License List found at
`<https://spdx.org/licenses/>`_. The list may not be up-to-date depending on how
recent your installation of :program:`reuse` is.

The list contains rows with three items each: the SPDX License Identifier, the
full name of the license, and an URL to the license.

Options
-------

.. option:: -j, --json

  Output the list as JSON.

.. option:: --help

  Display help and exit.
