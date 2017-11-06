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

"""Global fixtures and configuration."""

# pylint: disable=redefined-outer-name

import logging
import os
import shutil
import subprocess
from collections import namedtuple
from io import StringIO
from pathlib import Path
from typing import Dict, Tuple

import jinja2
import pytest
from click.testing import CliRunner

from reuse import LicenseInfo

CWD = Path.cwd()

TESTS_DIRECTORY = Path(__file__).parent.resolve()
RESOURCES_DIRECTORY = TESTS_DIRECTORY / 'resources'
CODE_FILES_DIRECTORY = RESOURCES_DIRECTORY / 'code_files'

# Some licenses to test against
LICENSES = [
    'CC0-1.0',
    'GPL-3.0+',
    '(GPL-2.0 OR BSD-3-Clause)',
]


NameAndLicense = namedtuple(
    'NameAndLicense',
    ['name', 'license_info'],
)


def pytest_configure(config):
    """Called after command line options have been parsed and all plugins and
    initial conftest files been loaded.
    """
    if config.getoption('--capture') == 'no':
        logging.basicConfig(level=logging.DEBUG)


def pytest_runtest_setup(item):
    """Called before running a test."""
    # pylint: disable=unused-argument
    # Make sure to restore CWD
    os.chdir(str(CWD))


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
                LicenseInfo((context['license'],), (context['license_file'],)))

            result[name_and_license] = template.render(context)

    return result


COMPILED_CODE_FILES = render_code_files()


@pytest.fixture()
def fake_repository(tmpdir_factory) -> Path:
    """Create a temporary fake repository."""
    directory = Path(str(tmpdir_factory.mktemp('code_files')))
    src = directory / 'src'
    debian_dir = directory / 'debian'
    src.mkdir()
    debian_dir.mkdir()

    rendered_texts = COMPILED_CODE_FILES

    for name_and_license, text in rendered_texts.items():
        (src / name_and_license.name).write_text(text)

    # debian/copyright
    shutil.copy(
        str(RESOURCES_DIRECTORY / 'debian/copyright'),
        str(debian_dir / 'copyright'))
    (src / 'no_license.py').touch()

    os.chdir(str(directory))
    return directory


@pytest.fixture()
def git_repository(fake_repository: Path) -> Path:
    """Create a git repository with ignored files."""
    subprocess.run(['git', 'init', str(fake_repository)])

    gitignore = "*.pyc\nbuild"
    (fake_repository / '.gitignore').write_text(gitignore)

    for file_ in (fake_repository / 'src').iterdir():
        if file_.suffix == '.py':
            file_.with_suffix('.pyc').touch()

    build_dir = fake_repository / 'build'
    build_dir.mkdir()
    (build_dir / 'hello.py').touch()

    os.chdir(str(fake_repository))
    return fake_repository


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
    directory = Path(str(tmpdir_factory.mktemp('empty_file_with_license')))

    key, value = request.param

    (directory / '{}.license'.format(key.name)).write_text(value)
    (directory / key.name).touch()

    os.chdir(str(directory))
    return (directory, key.license_info)


@pytest.fixture
def runner() -> CliRunner:
    """Return a click CLI runner."""
    return CliRunner()
