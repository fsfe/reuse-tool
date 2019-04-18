#!/usr/bin/env python3
#
# SPDX-Copyright: 2017-2018 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import glob
import shutil
import subprocess
from distutils import cmd
from distutils.command.build import build
from pathlib import Path
from warnings import warn

from setuptools import setup

requirements = ["python-debian", "spdx-tools", "license-expression"]

test_requirements = ["pytest"]


def readme_rst():
    """Return contents of README.rst"""
    return open("README.rst").read()


def changelog_rst():
    """Return contents of CHANGELOG.rst"""
    return open("CHANGELOG.rst").read()


def mo_files():
    """List all .mo files.

    This is a bit of a hack.  The files need to be renamed to "reuse.mo" for
    gettext to pick up on them.  So they're all moved into individual
    directories before being included.

    I really wish there were a better, standardised way to include
    translations, short of including them as package data.
    """
    paths = glob.glob("po/*.mo")
    result = []
    for path in paths:
        path = Path(path)
        lang_dir = Path("po") / path.stem
        lang_dir.mkdir(exist_ok=True)
        shutil.copyfile(path, lang_dir / "reuse.mo")
        result.append(
            (
                "share/locale/{}/LC_MESSAGES/".format(path.stem),
                [str(lang_dir / "reuse.mo")],
            )
        )
    return result


class BuildTrans(cmd.Command):
    """Command for compiling the .mo files."""

    user_options = []

    def initialize_options(self):
        self.po_files = None
        self.msgfmt = None

    def finalize_options(self):
        self.po_files = glob.glob("po/*.po")
        self.msgfmt = shutil.which("msgfmt")

    def run(self):
        if self.msgfmt:
            for po_file in self.po_files:
                subprocess.run(
                    [self.msgfmt, po_file, "-o", po_file.replace(".po", ".mo")]
                )
        else:
            warn("msgfmt is not installed. Translations will not be included.")


class Build(build):
    """Redefined build."""

    sub_commands = [("build_trans", None)] + build.sub_commands


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
        long_description=readme_rst() + "\n\n" + changelog_rst(),
        package_dir={"": "src"},
        packages=["reuse"],
        data_files=mo_files(),
        include_package_data=True,
        entry_points={"console_scripts": ["reuse = reuse._main:main"]},
        install_requires=requirements,
        tests_require=test_requirements,
        classifiers=[
            "Development Status :: 3 - Alpha",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: "
            "GNU General Public License v3 or later (GPLv3+)",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
        ],
        cmdclass={"build": Build, "build_trans": BuildTrans},
    )
