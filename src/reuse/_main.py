#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of reuse.  It is copyrighted by the contributors recorded
# in the version control history of the file, available from its original
# location: https://git.fsfe.org/carmenbianca/reuse
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

import click

# Import __init__.py.  I don't know how to do this cleanly
reuse = importlib.import_module('..', __name__)


@click.group()
@click.option('--debug/--no-debug', default=False)
def cli(debug):
    logging.basicConfig(level=logging.DEBUG if debug else logging.WARNING)

@cli.command()
@click.argument(
    'path', required=False, default='.', type=click.Path(exists=True))
@click.pass_context
def unlicensed(context, path):
    """List all unlicensed files.

    This prints only the paths of the files for which a licence could not be
    found, each file on a separate line.
    """
    counter = 0

    for file_ in reuse.unlicensed(path):
        click.echo(file_)
        counter += 1

    context.exit(counter)
