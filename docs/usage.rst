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
current year is 2019)::

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

The default template is::

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

An example of a custom template with manual commenting is::

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
