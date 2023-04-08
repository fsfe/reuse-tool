#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Carmen Bianca Bakker <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Script called by poetry. The API used by poetry is unstable, but let's hope
this stays functional.
"""

import glob
import logging
import os
import shutil
import subprocess
from pathlib import Path

_LOGGER = logging.getLogger(__name__)
ROOT_DIR = Path(os.path.dirname(__file__))
BUILD_DIR = ROOT_DIR / "build"
PO_DIR = ROOT_DIR / "po"


def mkdir_p(path):
    """Make directory and its parents."""
    Path(path).mkdir(parents=True, exist_ok=True)


def rm_fr(path):
    """Force-remove directory."""
    path = Path(path)
    if path.exists():
        shutil.rmtree(path)


def main():
    """Compile .mo files and move them into src directory."""
    rm_fr(BUILD_DIR)
    mkdir_p(BUILD_DIR)

    msgfmt = None
    for executable in ["msgfmt", "msgfmt.py", "msgfmt3.py"]:
        msgfmt = shutil.which(executable)
        if msgfmt:
            break

    if msgfmt:
        po_files = glob.glob(f"{PO_DIR}/*.po")
        mo_files = []

        # Compile
        for po_file in po_files:
            _LOGGER.info(f"compiling {po_file}")
            lang_dir = (
                BUILD_DIR / "reuse/locale" / Path(po_file).stem / "LC_MESSAGES"
            )
            mkdir_p(lang_dir)
            destination = Path(lang_dir) / "reuse.mo"
            subprocess.run(
                [
                    msgfmt,
                    "-o",
                    str(destination),
                    str(po_file),
                ],
                check=True,
            )
            mo_files.append(destination)

        # Move compiled files into src
        rm_fr(ROOT_DIR / "src/reuse/locale")
        for mo_file in mo_files:
            relative = (
                ROOT_DIR / Path("src") / os.path.relpath(mo_file, BUILD_DIR)
            )
            _LOGGER.info(f"copying {mo_file} to {relative}")
            mkdir_p(relative.parent)
            shutil.copyfile(mo_file, relative)


if __name__ == "__main__":
    main()
