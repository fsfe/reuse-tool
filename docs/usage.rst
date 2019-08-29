=====
Usage
=====

The :doc:`overview <readme>` documents some basic usage on how to use this tool.
It is highly recommended to read the overview first, and you might not even need
to read this chapter. This chapter covers details that might not be immediately
obvious when using the tool. This chapter does not cover *everything*, assuming
that the user is helped enough by ``reuse --help`` and ``reuse <subcommand>
--help``.

addheader
=========

``addheader`` makes it possible to semi-automatically add copyright and
licensing information into the header of a file. This is useful especially in
scenarios where you want to add a copyright holder or license to a lot of files
without having to manually edit the header of each file.

.. warning::
  You should be cautious with using ``addheader`` in automated processes. While
  nothing is stopping you from using it in your release script, you should make
  sure that the information it adds is actually reflective of reality. This is
  best verified manually.

The basic usage is ``reuse addheader --copyright="Jane Doe" --license=MIT
my_file.py``. This will add the following header to the file (assuming that the
current year is 2019):

.. code-block:: python

  # SPDX-FileCopyrightText: 2019 Jane Doe
  #
  # SPDX-License-Identifier: MIT

You can use as many ``--copyright`` and ``--copyright`` arguments, so long as
there is at least one such argument.

The REUSE header always starts at the first character in a file. If a different
REUSE header already existed, its tags are copied, and the header is replaced.
If the pre-existing comment header did not contain any copyright and licensing
information, it is moved downwards in the file. A shebang is always preserved.

Comment styles
--------------

The tool normally tries to auto-detect the comment style to use from the file
extension of a file, and use that comment style. If the tool is unable to detect
the comment style, or if it detects the wrong style, you can override the style
using ``--style``. The supported styles are:

- C
- CSS
- Haskell
- HTML
- ML
- Python
- TeX

If your comment style is not supported or a file extension is not correctly
detected, please `open an issue <https://github.com/fsfe/reuse-tool/issues>`_.

Templates
---------

When the tool adds a header to a file, it normally first lists all copyright
statements alphabetically, adds a single empty line, and then lists all SPDX
License Expressions alphabetically. That is all that the header contains. It is
possible to change this behaviour, and use a custom type of header that contains
extra text. This is done through Jinja2 templates.

The default template is:

.. code-block:: jinja

  {% for copyright_line in copyright_lines %}
  {{ copyright_line }}
  {% endfor %}

  {% for expression in spdx_expressions %}
  SPDX-License-Identifier: {{ expression }}
  {% endfor %}

Templates are automatically commented by the tool, depending on the detected or
specified comment style.

You can create your own Jinja2 templates and place them in
``.reuse/templates/``. If you create the template ``mytemplate.jinja2``, you can
use it with ``reuse addheader --copyright="Jane Doe" --template=mytemplate
foo.py``.

Inside of the template, you have access to the following variables:

- ``copyright_lines`` --- a list of copyright notices (string).
- ``spdx_expressions`` --- a list of SPDX License Expressions (string).

In the future, more variables will be added.

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

lint
====

``lint`` is the main component of the tool. Summarily, it verifies whether the
project is compliant with `the REUSE Specification
<https://reuse.software/spec/>`_. Its main goal is to find all files that do not
have copyright and licensing information in their headers, but it also checks a
few other things.

This is some example output of ``reuse lint``:

.. code-block:: text

  # MISSING COPYRIGHT AND LICENSING INFORMATION

  The following files have no copyright and licensing information:
  * no-information.txt


  # BAD LICENSES

  'bad-license' found in:
  * LICENSES/bad-license.txt


  # MISSING LICENSES

  'MIT' found in:
  * src/reuse/header.py


  # SUMMARY

  * Bad licenses: bad-license
  * Missing licenses: MIT
  * Unused licenses: bad-license
  * Used licenses: Apache-2.0, CC-BY-SA-4.0, CC0-1.0, GPL-3.0-or-later
  * Read errors: 0
  * Files with copyright information: 56 / 57
  * Files with license information: 56 / 57

  Unfortunately, your project is not compliant with version 3.0 of the REUSE Specification :-(

Implementation details
----------------------

The following implementation details might be relevant for your use of the tool.

The linter does not strictly limit itself to the header comment as prescribed by
the specification. It searches the first 4 kibibytes of the file for copyright
and licensing information. This makes sure that the linter can parse any type of
plain-text file, even if the comment style is not recognised.

If a file is found to have an unparseable tag, that file is not parsed at all.
This is `a bug <https://github.com/fsfe/reuse-tool/issues/4>`_.

The tool does not verify the correctness of copyright notices. It finds any line
beginning with '©', 'Copyright', or 'SPDX-FileCopyrightText:', then the tag and
everything following it is considered a valid copyright notice, even if the
copyright notice is not compliant with the specification.

When running ``reuse lint``, the root of the project is automatically found if
the working directory is inside a git repository. Otherwise, it treats the
working directory or the specified directory as the root of the project.

The STDOUT output of ``reuse lint`` is valid Markdown. Occasionally some logging
will be printed to STDERR, which is not valid Markdown.

Criteria
--------

These are the criteria that the linter checks against:

Bad licenses
++++++++++++

Licenses that are found in ``LICENSES/`` that are not found in the SPDX License
List or do not start with ``LicenseRef-`` are bad licenses.

Missing licenses
++++++++++++++++

If a license is referred to in a comment header, but the license is not found in
the ``LICENSES/`` directory, then that license is missing.

Unused licenses
+++++++++++++++

Conversely, if a license is found in the ``LICENSES/`` directory but is not
referred to in any comment header, then that license is unused.

Read errors
+++++++++++

Not technically a criterion, but files that cannot be read by the operating
system are read errors, and need to be fixed.

Files with copyright and license information
++++++++++++++++++++++++++++++++++++++++++++

Every file needs to have copyright and licensing information associated with it.
The REUSE Specification details several ways of doing it. By and large, these
are the methods:

- Placing tags in the header of the file.
- Placing tags in a ``.license`` file adjacent to the file.
- Putting the information in the DEP5 file.

If a file is found that does not have copyright and/or license information
associated with it, then the project is not compliant.
