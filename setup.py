#!/usr/bin/env python3
#
# SPDX-Copyright: 2017-2018 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import glob
import shutil
import subprocess
from distutils import cmd
from pathlib import Path
from warnings import warn

from setuptools import setup
from setuptools.command.build_py import build_py

requirements = ["python-debian", "spdx-tools", "license-expression"]

test_requirements = ["pytest"]


def readme_rst():
    """Return contents of README.rst"""
    return open("README.rst").read()


def changelog_rst():
    """Return contents of CHANGELOG.rst"""
    return open("CHANGELOG.rst").read()


def mo_files():
    """List all .mo files."""
    paths = glob.glob("build/locale/**/**/*.mo")
    result = []
    for path in paths:
        path = Path(path)
        result.append(
            (
                "share/locale/{}/LC_MESSAGES/".format(path.parent.parent.name),
                [str(path)],
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
        for msgfmt in ["msgfmt", "msgfmt.py", "msgfmt3.py"]:
            self.msgfmt = shutil.which(msgfmt)
            break

    def run(self):
        if self.msgfmt:
            for po_file in self.po_files:
                self.announce("compiling {}".format(po_file))
                lang_dir = (
                    Path("build/locale") / Path(po_file).stem / "LC_MESSAGES"
                )
                lang_dir.mkdir(parents=True, exist_ok=True)
                subprocess.run(
                    [self.msgfmt, po_file, "-o", str(lang_dir / "reuse.mo")]
                )
            self.distribution.data_files = mo_files()
        else:
            warn("msgfmt is not installed. Translations will not be included.")


class Build(build_py):
    """Redefined build."""

    def run(self):
        self.run_command("build_trans")
        super().run()


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
        data_files=mo_files(),  # This is potentially re-set in build_trans!
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
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
        ],
        cmdclass={"build_py": Build, "build_trans": BuildTrans},
    )
