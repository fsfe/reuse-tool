#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of reuse.  It is copyrighted by the contributors recorded
# in the version control history of the file, available from its original
# location: https://git.fsfe.org/reuse/reuse
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
# License-Filename: LICENSES/GPL-3.0.txt

"""Entry functions for reuse."""

import importlib
import logging
from pathlib import Path
from pipes import quote

import click

from ._util import find_root

# Import __init__.py.  I don't know how to do this cleanly
reuse = importlib.import_module('..', __name__)  # pylint: disable=invalid-name

_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def _create_project() -> reuse.Project:
    """Create a project object.  Try to find the project root from $PWD,
    otherwise treat $PWD as root.
    """
    root = find_root()
    if root is None:
        root = Path.cwd()
    return reuse.Project(root)


@click.group()
@click.option(
    '--ignore-debian',
    is_flag=True,
    help='Do not use debian/copyright to extract license information')
@click.option(
    '--debug',
    is_flag=True,
    help='Enable debug statements')
@click.pass_context
def cli(context, debug, ignore_debian):
    """TODO: docstring"""
    logging.basicConfig(level=logging.DEBUG if debug else logging.WARNING)
    context.obj = dict()
    context.obj['ignore_debian'] = ignore_debian



@cli.command()
@click.argument(
    'paths', nargs=-1, type=click.Path(exists=True))
@click.pass_context
def license(context, paths):
    """Print the licenses and corresponding license files of each provided
    file.
    """
    project = _create_project()
    first = True
    for path in paths:
        if not first:
            click.echo()
        try:
            license_info = project.license_info_of(
                path,
                ignore_debian=context.obj['ignore_debian'])
        except IsADirectoryError:
            context.fail('%s is a directory' % path)
        except IOError:
            context.fail('could not read %s' % path)
        except reuse.LicenseInfoNotFound:
            license_info = reuse.LicenseInfo(['none'], ['none'])
        if not license_info.filenames:
            license_info.filenames = ['none']
        click.echo(quote(str(path)))
        click.echo(' '.join(map(quote, license_info.licenses)))
        click.echo(' '.join(map(quote, license_info.filenames)))

        first = False


@cli.command()
@click.argument(
    'path', required=False, default='.', type=click.Path(exists=True))
@click.pass_context
def lint(context, path):
    """List all unlicensed (non-compliant) files.

    This prints only the paths of the files for which a licence could not be
    found, each file on a separate line.
    """
    counter = 0

    project = _create_project()
    for file_ in project.unlicensed(
            path,
            ignore_debian=context.obj['ignore_debian']):
        click.echo(quote(str(file_)))
        counter += 1

    context.exit(counter)
