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

from pathlib import Path
from typing import Dict

import pytest
import jinja2

TESTS_DIRECTORY = Path(__file__).parent.resolve()
RESOURCES_DIRECTORY = TESTS_DIRECTORY / 'resources'
CODE_FILES_DIRECTORY = RESOURCES_DIRECTORY / 'code_files'

def render_code_files(license: str, license_file: str) -> Dict[str, str]:
    """Compile all code files with Jinja2 and return a dictionary with the
    filename as key, and rendered text as value.
    """
    loader = jinja2.FileSystemLoader(str(CODE_FILES_DIRECTORY))
    environment = jinja2.Environment(loader=loader)
    context = {
        'license': license,
        'license_file': license_file,
    }

    result = dict()

    for file_ in CODE_FILES_DIRECTORY.iterdir():
        if not file_.is_file():
            continue

        template = environment.get_template(file_.name)
        result[file_.name] = template.render(context)

    return result

@pytest.fixture(scope='session')
def fake_repository(tmpdir_factory) -> Path:
    """Create a temporary fake repository.

    .. IMPORTANT::
        Do not write into this directory.
    """
    directory = Path(tmpdir_factory.mktemp('code_files'))
    src = directory / 'src'
    src.mkdir()

    rendered_texts = render_code_files('GPL-3.0', 'LICENSES/GPL-3.0.txt')

    for name, text in rendered_texts.items():
        with (src / name).open('w') as out:
            out.write(text)

    return directory
