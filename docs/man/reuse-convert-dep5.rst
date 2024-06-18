..
  SPDX-FileCopyrightText: 2024 Free Software Foundation Europe e.V. <https://fsfe.org>

  SPDX-License-Identifier: CC-BY-SA-4.0

reuse-convert-dep5
==================

Synopsis
--------

**reuse convert-dep5** [*options*]

Description
-----------

:program:`reuse-convert-dep5` converts the ``.reuse/dep5`` file into a
functionally equivalent ``REUSE.toml`` file in the root of the project. The
``.reuse/dep5`` file is subsequently deleted.

Options
-------

.. option:: -h, --help

  Display help and exit.

Examples
--------

Given the following ``.reuse/dep5`` file::

  Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
  Upstream-Name: Some project
  Upstream-Contact: Jane Doe
  Source: https://example.com/
  Disclaimer: Some rights reserved

  Files: hello*.txt
  Copyright: 2018 Jane Doe
  License: MIT
  Comment: hello world

  Files: foo bar
  Copyright: 2018 Jane Doe
      2019 John Doe
  License: MIT

The following ``REUSE.toml`` is generated:

.. code-block:: toml

  version = 1
  SPDX-PackageName = "Some project"
  SPDX-PackageSupplier = "Jane Doe"
  SPDX-PackageDownloadLocation = "https://example.com/"
  SPDX-PackageComment = "Some rights reserved"

  [[annotations]]
  path = "hello**.txt"
  precedence = "aggregate"
  SPDX-FileCopyrightText = "2018 Jane Doe"
  SPDX-License-Identifier = "MIT"
  SPDX-FileComment = "hello world"

  [[annotations]]
  path = ["foo", "bar"]
  precedence = "aggregate"
  SPDX-FileCopyrightText = ["2018 Jane Doe", "2019 John Doe"]
  SPDX-License-Identifier = "MIT"
