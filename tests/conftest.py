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

"""Global fixtures and configuration."""

from collections import namedtuple
from io import StringIO
from pathlib import Path
from typing import Dict, Tuple

import jinja2
import pytest

from reuse.licenses import LICENSES
from reuse import LicenseInfo

TESTS_DIRECTORY = Path(__file__).parent.resolve()
RESOURCES_DIRECTORY = TESTS_DIRECTORY / 'resources'
CODE_FILES_DIRECTORY = RESOURCES_DIRECTORY / 'code_files'


NameAndLicense = namedtuple(
    'NameAndLicense',
    ['name', 'license_info'],
)


def render_code_files() -> Dict[NameAndLicense, str]:
    """Compile all code files with Jinja2 and return a dictionary with the
    file as key, and rendered text as value.
    """
    loader = jinja2.FileSystemLoader(str(CODE_FILES_DIRECTORY))
    environment = jinja2.Environment(loader=loader)

    result = dict()

    for file_ in CODE_FILES_DIRECTORY.iterdir():
        if not file_.is_file():
            continue

        template = environment.get_template(file_.name)

        for license in LICENSES:
            context = {
                'license': license,
                'license_file': 'LICENSES/{}.txt'.format(license),
            }

            # Put some related information in a struct-like object.
            name_and_license = NameAndLicense(
                '{}___{}'.format(license, file_.name),
                LicenseInfo(context['license'], context['license_file']))

            result[name_and_license] = template.render(context)

    return result


COMPILED_CODE_FILES = render_code_files()


@pytest.fixture(scope='session')
def fake_repository(tmpdir_factory) -> Path:
    """Create a temporary fake repository.

    .. IMPORTANT::
        Do not write into this directory.
    """
    directory = Path(tmpdir_factory.mktemp('code_files'))
    src = directory / 'src'
    src.mkdir()

    rendered_texts = COMPILED_CODE_FILES

    for name_and_license, text in rendered_texts.items():
        with (src / name_and_license.name).open('w') as out:
            out.write(text)

    return directory


@pytest.fixture(params=COMPILED_CODE_FILES.items())
def file_with_license_comments(request) -> StringIO:
    """Provide a code file that has REUSE license information in its header
    comments.

    The code file is a fake file (StringIO).  It contains additional attributes
    for the test to read.
    """
    key, value = request.param
    result = StringIO(value)
    result.name = key.name
    result.license_info = key.license_info
    yield result


@pytest.fixture(params=COMPILED_CODE_FILES.items(), scope='session')
def empty_file_with_license_file(
        request, tmpdir_factory) -> Tuple[Path, LicenseInfo]:
    """Create a temporary directory that contains two files:  The code file and
    the license file.
    """
    directory = Path(tmpdir_factory.mktemp('empty_file_with_license'))

    key, value = request.param
    with (directory / '{}.license'.format(key.name)).open('w') as out:
        out.write(value)

    with (directory / key.name).open('w') as out:
        out.write('')

    return (directory, key.license_info)
