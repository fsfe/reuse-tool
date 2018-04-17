# -*- coding: utf-8 -*-
#
# Copyright (C) 2017  Free Software Foundation Europe e.V.
# Copyright (C) 2018  Carmen Bianca Bakker
#
# This file is part of reuse, available from its original location:
# <https://git.fsfe.org/reuse/reuse/>.
#
# reuse is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# reuse is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# reuse.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Entry functions for reuse."""

import argparse
import importlib
import logging
import sys
from gettext import gettext as _
from pathlib import Path
from pipes import quote
from typing import List

from ._format import INDENT, fill_all, fill_paragraph
from ._util import GIT_METHOD, find_root, setup_logging

# Import __init__.py.  I don't know how to do this cleanly
reuse = importlib.import_module('..', __name__)  # pylint: disable=invalid-name

_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

_DESCRIPTION_LINES = [
    _('reuse  Copyright (C) 2017-2018  Free Software Foundation Europe e.V.'),

    _(
        'reuse is a tool for compliance with the REUSE Initiative '
        'recommendations.  See <https://reuse.software/> for more '
        'information.'),

    _(
        # Translators: Find an (un)official translation of the GPL for this
        # bit.
        'reuse is free software: you can redistribute it and/or modify it '
        'under the terms of the GNU General Public License as published by '
        'the Free Software Foundation, either version 3 of the License, or '
        '(at your option) any later version.\n'
        '\n'
        'reuse is distributed in the hope that it will be useful, but WITHOUT '
        'ANY WARRANTY; without even the implied warranty of MERCHANTABILITY '
        'or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public '
        'License for more details.\n'
        '\n'
        'You should have received a copy of the GNU General Public License '
        'along with reuse.  If not, see <http://www.gnu.org/licenses/>.'),

    _("Support the FSFE's work:")]

_INDENTED_LINE = _(
    'Donations are critical to our strength and autonomy.  They enable us to '
    'continue working for Free Software wherever necessary.  Please consider '
    'making a donation at <https://fsfe.org/donate/>.')

_DESCRIPTION_TEXT = (
    fill_all('\n\n'.join(_DESCRIPTION_LINES))
    + '\n\n'
    + fill_paragraph(_INDENTED_LINE, indent_width=INDENT))


_EPILOG_TEXT = ''
_PYGIT2_WARN = '\n\n'.join([
    _('IMPORTANT:'),

    fill_paragraph(
        _(
            'You do not have pygit2 installed.  reuse will slow down '
            'significantly because of this.  For better performance, please '
            "install your distribution's version of pygit2."),
        indent_width=INDENT)])
if not GIT_METHOD == 'pygit2':
    _EPILOG_TEXT = _EPILOG_TEXT + '\n\n' + _PYGIT2_WARN


def _create_project() -> reuse.Project:
    """Create a project object.  Try to find the project root from $PWD,
    otherwise treat $PWD as root.
    """
    root = find_root()
    if root is None:
        root = Path.cwd()
    return reuse.Project(root)


def compile(args, out=sys.stdout):
    """Print the project's bill of materials."""
    project = _create_project()
    if args.output:
        out = args.output
        if not out.name.endswith('.spdx'):
            # Translators: %s is a file name.
            _logger.warning(_('%s does not end with .spdx'), out.name)
    project.bill_of_materials(
        out,
        ignore_debian=args.ignore_debian)

    return 0


def license(args, out=sys.stdout):
    """Print the SPDX expressions of each provided file."""
    project = _create_project()
    first = True

    for path in args.paths:
        try:
            reuse_info = project.reuse_info_of(
                path,
                ignore_debian=args.ignore_debian)
        except IsADirectoryError:
            _logger.error(_('%s is a directory'), path)
            continue
        except IOError:
            # Translators: %s is a file.
            _logger.error(_('could not read %s'), path)
            continue

        if not first:
            out.write('\n')

        out.write(quote(str(path)))
        out.write('\n')

        if any(reuse_info.spdx_expressions):
            out.write(', '.join(map(quote, reuse_info.spdx_expressions)))
            out.write('\n')
        else:
            out.write(_('none\n'))

        first = False

    return 0


def lint(args, out=sys.stdout):
    """List all non-compliant files."""
    counter = 0
    found = set()

    project = _create_project()
    paths = args.paths
    if not paths:
        paths = [project.root]

    for path in paths:
        for file_ in project.lint(
                path,
                spdx_mandatory=args.spdx_mandatory,
                copyright_mandatory=args.copyright_mandatory,
                ignore_debian=args.ignore_debian,
                ignore_missing=args.ignore_missing):
            output = quote(str(file_))
            if output not in found:
                out.write(output)
                out.write('\n')
                found.add(output)
                counter += 1

    return counter


def parser() -> argparse.ArgumentParser:
    """Create the parser and return it."""
    # pylint: disable=redefined-outer-name
    parser = argparse.ArgumentParser(
        'reuse', formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(_DESCRIPTION_TEXT), epilog=_EPILOG_TEXT)
    parser.add_argument(
        '--debug', action='store_true', help=_('enable debug statements'))
    parser.add_argument(
        '--ignore-debian', action='store_true',
        help=_('do not use debian/copyright to extract reuse information'))
    parser.add_argument(
        '--version', action='store_true',
        help=_("show program's version number and exit"))
    parser.set_defaults(func=lambda x, y: parser.print_help())

    subparsers = parser.add_subparsers()

    compile_parser = subparsers.add_parser(
        'compile',
        help=_("print the project's bill of materials"))
    compile_parser.add_argument(
        '--output', '-o', action='store', type=argparse.FileType('w'))
    compile_parser.set_defaults(func=compile)

    lint_parser = subparsers.add_parser(
        'lint', formatter_class=argparse.RawDescriptionHelpFormatter,
        help=_('list all non-compliant files'),
        description=fill_all(_(
            'List all non-compliant files.\n'
            '\n'
            'A file is non-compliant when:\n'
            '\n'
            '- It has no copyright information.\n'
            '\n'
            '- It has no license (declared as SPDX expression).\n'
            '\n'
            '- Its license could not be found.\n'
            '\n'
            'This prints only the paths of the files that do not comply, each '
            'file on a separate line.\n'
            '\n'
            'Error and warning messages are output to STDERR.')))
    lint_parser.add_argument(
        'paths', action='store', nargs='*')
    lint_parser.add_argument(
        '--spdx-mandatory', action='store_true', default=True,
        help=_('SPDX expressions are mandatory for compliance'))
    lint_parser.add_argument(
        '--copyright-mandatory', action='store_true', default=True,
        help=_('copyright notices are mandatory for compliance'))
    lint_parser.add_argument(
        '--ignore-missing', action='store_true',
        help=_('ignore missing licenses'))
    lint_parser.set_defaults(func=lint)

    license_parser = subparsers.add_parser(
        'license',
        help=_('print the SPDX expressions of each provided file'))
    license_parser.add_argument(
        'paths', action='store', nargs='*')
    license_parser.set_defaults(func=license)

    return parser


def main(args: List[str] = None, out=sys.stdout) -> None:
    """Main entry function."""
    if args is None:
        args = sys.argv[1:]

    main_parser = parser()
    parsed_args = main_parser.parse_args(args)

    setup_logging(
        level=logging.DEBUG if parsed_args.debug else logging.WARNING)

    if parsed_args.version:
        out.write(_('reuse, version {}\n').format(reuse.__version__))
        return 0
    return parsed_args.func(parsed_args, out)
