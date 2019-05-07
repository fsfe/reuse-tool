#!/usr/bin/env python3
#
# SPDX-Copyright: 2017-2018 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import glob
import os
from pathlib import Path

from setuptools import setup

requirements = ["python-debian", "spdx-tools", "license-expression"]

test_requirements = ["pytest"]


def readme_rst():
    return open("README.rst").read()


def mo_files():
    paths = glob.glob("po/**/**/reuse.mo")
    return [
        ("share/locale/{}/LC_MESSAGES".format(Path(path).parts[1]), [path])
        for path in paths
    ]


if __name__ == "__main__":
    setup(
        name="fsfe-reuse",
        version="0.4.0a1",
        url="https://github.com/fsfe/reuse-tool",
        license="GPL-3.0-or-later",
        author="Carmen Bianca Bakker",
        author_email="carmenbianca@fsfe.org",
        description="reuse is a tool for compliance with the REUSE Initiative "
        "recommendations.",
        long_description=readme_rst(),
        package_dir={"": "src"},
        packages=["reuse"],
        data_files=mo_files(),
        entry_points={"console_scripts": ["reuse = reuse._main:main"]},
        install_requires=requirements,
        tests_require=test_requirements,
        classifiers=[
            "Development Status :: 3 - Alpha",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: "
            "GNU General Public License v3 or later (GPLv3+)",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
        ],
    )
