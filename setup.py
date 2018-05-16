#!/usr/bin/env python3
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

import os
import glob
import subprocess
from pathlib import Path

from setuptools import setup

requirements = [
    'chardet',
    'python-debian',
]
git_extras = []

if not os.environ.get('REUSE_DEV'):
    git_extras.append('pygit2')

test_requirements = [
    'pytest',
    'jinja2',
]


def readme_rst():
    try:
        command = ['pandoc', 'README.md', '-t', 'rst']
        result = subprocess.run(command, stdout=subprocess.PIPE)
        return result.stdout.decode('utf-8')
    except FileNotFoundError:
        if os.environ.get('RST_ERROR'):
            raise
        return open('README.md').read()


def mo_files():
    paths = glob.glob('po/**/**/reuse.mo')
    return [
        ('share/locale/{}/LC_MESSAGES'.format(Path(path).parts[1]), [path])
        for path in paths]


if __name__ == '__main__':
    setup(
        name='fsfe-reuse',
        version='0.3.0',
        url='https://git.fsfe.org/reuse/reuse',
        license='GPL-3.0-or-later',

        author='Carmen Bianca Bakker',
        author_email='carmenbianca@fsfe.org',

        description='reuse is a tool for compliance with the REUSE Initiative '
            'recommendations.',
        long_description=readme_rst(),

        package_dir={
            '': 'src'
        },
        packages=[
            'reuse',
        ],

        data_files=mo_files(),

        entry_points={
            'console_scripts': [
                'reuse = reuse._main:main',
            ],
        },

        install_requires=requirements,
        tests_require=test_requirements,
        extras_require={
            'git': git_extras,
        },

        classifiers=[
            'Development Status :: 3 - Alpha',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: '
            'GNU General Public License v3 or later (GPLv3+)',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
        ],
    )
