#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2017  Free Software Foundation Europe e.V.
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
# SPDX-License-Identifier: GPL-3.0+

"""Entry functions for reuse."""

import importlib
import logging
import sys
from pathlib import Path
from pipes import quote

import click

from ._util import find_root, setup_logging

# Import __init__.py.  I don't know how to do this cleanly
reuse = importlib.import_module('..', __name__)  # pylint: disable=invalid-name

_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

_EPILOG_TEXT = ''
_PYGIT2_WARN = (
    """
IMPORTANT:

  You do not have pygit2 installed.  reuse will slow down significantly
because of this.

  For better performance, please install your distribution's version of
pygit2.""")
if not reuse.PYGIT2:
    _EPILOG_TEXT = _EPILOG_TEXT + '\n\n' + _PYGIT2_WARN


def _create_project() -> reuse.Project:
    """Create a project object.  Try to find the project root from $PWD,
    otherwise treat $PWD as root.
    """
    root = find_root()
    if root is None:
        root = Path.cwd()
    return reuse.Project(root)


@click.group(epilog=_EPILOG_TEXT)
@click.option(
    '--ignore-debian',
    is_flag=True,
    help='Do not use debian/copyright to extract reuse information.')
@click.option(
    '--debug',
    is_flag=True,
    help='Enable debug statements.')
@click.version_option(version=reuse.__version__)
@click.pass_context
def cli(context, debug, ignore_debian):
    """reuse  Copyright (C) 2017  Free Software Foundation Europe e.V.

    reuse is a tool for compliance with the REUSE Initiative recommendations.
    See <https://reuse.software/> for more information.

    reuse is free software: you can redistribute it and/or modify it under the
    terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later
    version.

    reuse is distributed in the hope that it will be useful, but WITHOUT ANY
    WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
    details.

    You should have received a copy of the GNU General Public License along
    with reuse.  If not, see <http://www.gnu.org/licenses/>.

    Support the FSFE's work:

      Donations are critical to our strength and autonomy.  They enable us to
      continue working for Free Software wherever necessary.  Please consider
      making a donation at <https://fsfe.org/donate/>.
    """
    setup_logging(level=logging.DEBUG if debug else logging.WARNING)
    context.obj = dict()
    context.obj['ignore_debian'] = ignore_debian

    if not reuse.PYGIT2:
        _logger.warning(_PYGIT2_WARN)


@cli.command()
@click.option(
    '--output', '-o',
    help='Write to file.',
    type=click.File('w'))
@click.pass_context
def compile(context, output):
    """Print the project's bill of materials."""
    project = _create_project()
    out = sys.stdout
    if output:
        out = output
        if not output.name.endswith('.spdx'):
            _logger.warning('%s does not end with .spdx', output.name)
    project.bill_of_materials(
        out,
        ignore_debian=context.obj['ignore_debian'])


@cli.command()
@click.argument(
    'paths', nargs=-1, type=click.Path(exists=True))
@click.pass_context
def license(context, paths):
    """Print the SPDX expressions of each provided file."""
    project = _create_project()
    first = True
    for path in paths:
        try:
            reuse_info = project.reuse_info_of(
                path,
                ignore_debian=context.obj['ignore_debian'])
        except IsADirectoryError:
            _logger.error('%s is a directory', path)
            continue
        except IOError:
            _logger.error('could not read %s', path)
            continue

        if not first:
            click.echo()

        click.echo(quote(str(path)))

        if any(reuse_info.spdx_expressions):
            click.echo(', '.join(map(quote, reuse_info.spdx_expressions)))
        else:
            click.echo('none')

        first = False


@cli.command()
@click.option(
    '--spdx-mandatory/--no-spdx-mandatory',
    default=True,
    help='SPDX expressions are mandatory for compliance.')
@click.option(
    '--copyright-mandatory/--no-copyright-mandatory',
    default=True,
    help='Copyright notices are mandatory for compliance.')
@click.option(
    '--ignore-missing',
    is_flag=True,
    help='Ignore missing licenses.')
@click.argument(
    'paths', required=False, nargs=-1, type=click.Path(exists=True))
@click.pass_context
def lint(context, paths, copyright_mandatory, spdx_mandatory, ignore_missing):
    """List all non-compliant files.

    A file is non-compliant when:

    - It has no copyright information.

    - It has no license (declared as SPDX expression).

    - Its license could not be found.

    This prints only the paths of the files for which a licence could not be
    found, each file on a separate line.

    Error and warning messages are output to STDERR.
    """
    counter = 0
    found = set()

    project = _create_project()
    if not paths:
        paths = [project.root]

    for path in paths:
        for file_ in project.lint(
                path,
                spdx_mandatory=spdx_mandatory,
                copyright_mandatory=copyright_mandatory,
                ignore_debian=context.obj['ignore_debian'],
                ignore_missing=ignore_missing):
            output = quote(str(file_))
            if output not in found:
                click.echo(output)
                found.add(output)
                counter += 1

    context.exit(counter)
