..
  SPDX-FileCopyrightText: 2024 Free Software Foundation Europe e.V. <https://fsfe.org>

  SPDX-License-Identifier: CC-BY-SA-4.0

reuse-spdx
==========

Synopsis
--------

**reuse spdx** [*options*]

Description
-----------

:program:`reuse-spdx` generates an SPDX bill of materials for the project.

The bill of materials is output to STDOUT.

..
  TODO: add more details here. Maybe wait until this is refactored.

Options
-------

.. option:: -o, --output FILE

  Write the bill of materials to a file instead of writing it to STDOUT.

.. option:: --add-license-concluded

  Instead of writing 'NOASSERTION' to LicenseConcluded, write an expression that
  is the logical equivalent of AND-ing all found expressions.

.. option:: --creator-person

  Name of the creator (person) of the bill of materials.

.. option:: --creator-organization

  Name of the creator (organization) of the bill of materials.

.. option:: -h, --help

  Display help and exit.
