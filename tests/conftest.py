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
# SPDX-License-Identifier: GPL-3.0-or-later

"""Global fixtures and configuration."""

# pylint: disable=redefined-outer-name

import logging
import os
import shutil
import subprocess
from collections import namedtuple
from io import StringIO
from pathlib import Path
from typing import Dict, Optional, Tuple

import jinja2
import pytest
from reuse import ReuseInfo
from reuse._util import GIT_EXE, GIT_METHOD, setup_logging

CWD = Path.cwd()

TESTS_DIRECTORY = Path(__file__).parent.resolve()
RESOURCES_DIRECTORY = TESTS_DIRECTORY / 'resources'
CODE_FILES_DIRECTORY = RESOURCES_DIRECTORY / 'code_files'

# Some licenses to test against
LICENSES = [
    'CC0-1.0',
    'GPL-3.0',
    'GPL-3.0+',
    'GPL-3.0-only',
    'GPL-3.0-or-later',
    '(GPL-2.0-only OR BSD-3-Clause)',
]

GIT_METHODS = [None]
if GIT_EXE:
    GIT_METHODS.append('git')
if GIT_METHOD == 'pygit2':
    GIT_METHODS.append('pygit2')


NameAndLicense = namedtuple(
    'NameAndLicense',
    ['name', 'reuse_info'],
)


def pytest_configure(config):
    """Called after command line options have been parsed and all plugins and
    initial conftest files been loaded.
    """
    if config.getoption('--capture') == 'no':
        setup_logging(level=logging.DEBUG)


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
        if file_.suffix == '.license':
            continue

        template = environment.get_template(file_.name)

        for license in LICENSES:
            context = {
                'license': license,
            }

            # Put some related information in a struct-like object.
            name_and_license = NameAndLicense(
                '{}___{}'.format(license, file_.name),
                ReuseInfo(
                    (context['license'],),
                    ('Copyright (C) 2017  Free Software Foundation Europe '
                     'e.V.',)))

            result[name_and_license] = template.render(context)

    return result


COMPILED_CODE_FILES = render_code_files()


@pytest.fixture(autouse=True, params=GIT_METHODS)
def git_method(request, monkeypatch) -> Optional[str]:
    """Run the test with multiple methods of git usage."""
    monkeypatch.setattr('reuse.GIT_METHOD', request.param)
    monkeypatch.setattr('reuse._util.GIT_METHOD', request.param)
    yield request.param


@pytest.fixture()
def tiny_repository(tmpdir_factory) -> Path:
    """Create a tiny temporary fake repository."""
    directory = Path(str(tmpdir_factory.mktemp('tiny')))
    src = directory / 'src'
    debian_dir = directory / 'debian'
    licenses_dir = directory / 'LICENSES'
    src.mkdir()
    debian_dir.mkdir()
    licenses_dir.mkdir()

    text = """
    # Copyright (C) 2017  Free Software Foundation Europe e.V.
    #
    # SPDX-License-Identifier: GPL-3.0+
    """
    (src / 'code.py').write_text(text)
    (src / 'no_license.py').touch()

    shutil.copy(
        str(RESOURCES_DIRECTORY / 'debian/copyright'),
        str(debian_dir / 'copyright'))

    # Fake text
    (licenses_dir / 'GPL-3.0.txt').write_text('GPL-3.0')

    os.chdir(str(directory))
    return directory


@pytest.fixture()
def empty_directory(tmpdir_factory) -> Path:
    """Create a temporary empty directory."""
    directory = Path(str(tmpdir_factory.mktemp('empty_directory')))

    os.chdir(str(directory))
    return directory


@pytest.fixture()
def fake_repository(tmpdir_factory) -> Path:
    """Create a temporary fake repository."""
    directory = Path(str(tmpdir_factory.mktemp('fake_repository')))
    src = directory / 'src'
    src.mkdir()
    debian_dir = directory / 'debian'
    debian_dir.mkdir()
    licenses_dir = directory / 'LICENSES'
    licenses_dir.mkdir()
    doc = directory / 'doc'
    doc.mkdir()

    rendered_texts = COMPILED_CODE_FILES

    for name_and_license, text in rendered_texts.items():
        (src / name_and_license.name).write_text(text)

    # debian/copyright
    shutil.copy(
        str(RESOURCES_DIRECTORY / 'debian/copyright'),
        str(debian_dir / 'copyright'))
    (doc / 'index.rst').touch()

    (directory / 'README.md').write_text(
        """
        # Copyright (C) 2017  Free Software Foundation Europe e.V.
        #
        # SPDX-License-Identifier: CC0-1.0
        # License-Filename: LICENSES/CC0-1.0
        """)

    # TODO: Write full licence texts
    licenses = ['CC0-1.0', 'GPL-3.0', 'GPL-2.0', 'BSD-3-Clause']
    for license in licenses:
        (licenses_dir / '{}.txt'.format(license)).touch()

    os.chdir(str(directory))
    return directory


@pytest.fixture()
def git_repository(fake_repository: Path, git_method: Optional[str]) -> Path:
    """Create a git repository with ignored files."""
    if git_method is None:
        pytest.skip('cannot run this test without git')

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
    result.reuse_info = key.reuse_info
    yield result


@pytest.fixture(params=COMPILED_CODE_FILES.items(), scope='session')
def empty_file_with_license_file(
        request, tmpdir_factory) -> Tuple[Path, ReuseInfo]:
    """Create a temporary directory that contains two files:  The code file and
    the license file.
    """
    directory = Path(str(tmpdir_factory.mktemp('empty_file_with_license')))

    key, value = request.param

    (directory / '{}.license'.format(key.name)).write_text(value)
    (directory / key.name).touch()

    os.chdir(str(directory))
    return (directory, key.reuse_info)
