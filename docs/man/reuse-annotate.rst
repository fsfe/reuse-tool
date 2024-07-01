..
  SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
  SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>

  SPDX-License-Identifier: CC-BY-SA-4.0

..
  REUSE-IgnoreStart

reuse-annotate
==============

Synopsis
--------

**reuse annotate** [*options*] [*file* ...]

Description
-----------

:program:`reuse-annotate` adds REUSE information into the headers of files. This
is useful especially in scenarios where you want to add a copyright holder or
license to a lot of files without having to manually edit the header of each
file.

.. warning::
  You should be cautious with using ``annotate`` in automated processes. While
  nothing is stopping you from using it in your release script, you should make
  sure that the information it adds is actually reflective of reality. This is
  best verified manually.

The REUSE header is placed at the very top of the file, excepting certain
existing headers like shebangs (``#!``) or XML declarations (``<?xml
version="1.0"?>``). If a different header containing copyright or licensing
information already exists in the file---at the top or elsewhere---that header
is replaced in-place with the additionally supplied REUSE information.

The tool tries to auto-detect the comment style to use from the file extension
of a file, and use that comment style.

Normally, the tool uses a single-line comment style when one is available (e.g.,
``//`` is used instead of ``/* ... */`` for C++ comment styles). If no single-line
comment style is available, a multi-line style is used.

Mandatory options
-----------------

At least *one* among the following options is required. They contain the
information which the tool will add to the file(s).

.. option:: -c, --copyright COPYRIGHT

  A copyright holder. This does not contain the year or the copyright prefix.
  See :option:`--year` and :option:`--copyright-prefix` for the year and prefix.
  This option can be repeated.

.. option:: -l, --license LICENSE

  An SPDX license identifier. This option can be repeated.

.. option:: --contributor CONTRIBUTOR

  A name of a contributor. The contributor will be added via the
  ``SPDX-FileContributor:`` tag. This option can be repeated.

Other options
-------------

.. option:: -y, --year YEAR

  Define the year of the copyright statement(s). If not defined, the year
  defaults to the current year.

.. option:: -s, --style STYLE

  Override the comment style detection mechanism to force a comment style on the
  files. This is useful when a file extension is not recognised, or when a file
  extension is associated with a comment style that you disagree with.

.. option:: --copyright-prefix PREFIX

  The prefix to use in the copyright statement. If not defined, ``spdx`` is used
  as prefix. The available copyright prefixes are:

  .. code-block::

    spdx:           SPDX-FileCopyrightText: <year> <statement>
    spdx-c:         SPDX-FileCopyrightText: (C) <year> <statement>
    spdx-symbol:    SPDX-FileCopyrightText: © <year> <statement>
    string:         Copyright <year> <statement>
    string-c:       Copyright (C) <year> <statement>
    string-symbol:  Copyright © <year> <statement>
    symbol:         © <year> <statement>

.. option:: -t, --template TEMPLATE

  The template to use for the comment header. The template name match the name
  of the template in ``.reuse/templates/``, without the ``.jinja2`` or
  ``.commented.jinja2`` suffix.

.. option:: --exclude-year

  Do not include the year in the copyright notice.

.. option:: --merge-copyrights

  If two (or more) copyright notices are identical except for their years,
  output them as a single line with the years combined.

.. option:: --single-line

  Force the tool to use a single-line comment style. For C, this would be
  ``//``.

.. option:: --multi-line

  Force the tool to use a multi-line comment style. For C, this would be
  ``/* ... */``.

.. option:: -r, --recursive

  Annotate all files recursively under the specified path.

.. option:: --no-replace

  Instead of replacing the first header in the file which contains copyright and
  licensing information, keep it and create a new header at the top.

.. option:: --force-dot-license

  Always write a .license file instead of trying to write into the file itself.

.. option:: --fallback-dot-license

  Instead of aborting when a file extension does not have an associated comment
  style, create a .license file for those files.

.. option:: --skip-unrecognised

  Instead of aborting when a file extension does not have an associated comment
  style, skip those files.

.. option:: -h, --help

  Display help and exit.

Templates
---------

When the tool adds a header to a file, it normally first lists all copyright
statements alphabetically, subsequently all contributors, then adds a single
empty line, and finally lists all SPDX License Expressions alphabetically. It is
possible to change this behaviour, and use a custom type of header that contains
extra text. This is done through Jinja2 templates.

The default template is:

.. code-block:: jinja

  {% for copyright_line in copyright_lines %}
  {{ copyright_line }}
  {% endfor %}
  {% for contributor_line in contributor_lines %}
  SPDX-FileContributor: {{ contributor_line }}
  {% endfor %}

  {% for expression in spdx_expressions %}
  SPDX-License-Identifier: {{ expression }}
  {% endfor %}

Templates are automatically commented by the tool, depending on the detected or
specified comment style.

You can create your own Jinja2 templates and place them in
``.reuse/templates/``. You must suffix your template with ``.jinja2``.

Inside of the template, you have access to the following variables:

- ``copyright_lines`` --- a list of copyright notices (string).
- ``contributor_lines`` --- a list of contributors (string).
- ``spdx_expressions`` --- a list of SPDX License Expressions (string).

In the future, more variables may be added.

In some cases, you might want to do custom comment formatting. In those cases,
you can pre-format your header as a comment. When doing so, suffix your template
with ``.commented.jinja2``.

An example of a custom template with manual commenting is:

.. code-block:: jinja

  /*
  {% for copyright_line in copyright_lines %}
   * {{ copyright_line }}
  {% endfor %}
  {% if copyright_lines and spdx_expressions %}
   *
  {% endif %}
  {% for expression in spdx_expressions %}
   * SPDX-License-Identifier: {{ expression }}
  {% endfor %}
  {% if "GPL-3.0-or-later" in spdx_expressions %}
   *
   * This program is free software: you can redistribute it and/or modify it under
   * the terms of the GNU General Public License as published by the Free Software
   * Foundation, either version 3 of the License, or (at your option) any later
   * version.
   *
   * This program is distributed in the hope that it will be useful, but WITHOUT
   * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
   * FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
   *
   * You should have received a copy of the GNU General Public License along with
   * this program. If not, see <https://www.gnu.org/licenses/>.
  {% endif %}
   */

Examples
--------

The basic usage is ``reuse annotate --copyright="Jane Doe" --license=MIT
my_file.py``. This will add the following header to the file (assuming that the
current year is 2019):

.. code-block:: python

  # SPDX-FileCopyrightText: 2019 Jane Doe
  #
  # SPDX-License-Identifier: MIT
