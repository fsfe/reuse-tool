#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

requirements = [
    # Add requirements
]

test_requirements = [
    'pytest',
]

if __name__ == '__main__':
    setup(
        name='reuse',
        version='0.0.1',
        url='https://git.fsfe.org/carmenbianca/reuse',

        author='Carmen Bianca Bakker',
        author_email='carmenbianca@fsfe.org',

        description='reuse is a tool for REUSE compliance.',
        long_description='TODO: long description',

        package_dir={
            '': 'src'
        },
        packages=[
            'reuse',
        ],

        entry_points={
        },

        install_requires=requirements,
        tests_require=test_requirements,

        classifiers=[
            'Development Status :: 2 - Pre-Alpha',
            'License :: OSI Approved :: '
            'GNU General Public License v3 or later (GPLv3+)',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
        ],
    )
