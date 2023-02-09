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
import os
import shutil
import subprocess
from pathlib import Path
from warnings import warn

from setuptools import Distribution
from setuptools.command.build_py import build_py

# pylint: disable=attribute-defined-outside-init


class Build(build_py):
    """Redefined build."""

    def initialize_options(self):
        super().initialize_options()
        self.po_files = None
        self.msgfmt = None
        self.mo_outputs = []

    def finalize_options(self):
        super().finalize_options()
        self.po_files = glob.glob("po/*.po")
        for msgfmt in ["msgfmt", "msgfmt.py", "msgfmt3.py"]:
            self.msgfmt = shutil.which(msgfmt)
            if self.msgfmt:
                break

    def run(self):
        super().run()
        if self.msgfmt:
            for po_file in self.po_files:
                self.announce(f"compiling {po_file}")
                lang_dir = str(
                    Path(self.build_lib)
                    / "reuse/locale"
                    / Path(po_file).stem
                    / "LC_MESSAGES"
                )
                destination = str(Path(lang_dir) / "reuse.mo")
                compile_func = lambda msgfmt, in_file, out: subprocess.run(
                    [msgfmt, in_file, "-o", out],
                    check=True,
                )

                self.mkpath(lang_dir)
                self.make_file(
                    po_file,
                    destination,
                    compile_func,
                    (self.msgfmt, po_file, destination),
                )
                self.mo_outputs.append(destination)

        else:
            warn("msgfmt is not installed. Translations will not be included.")

    def get_outputs(self, include_bytecode=1):
        return (
            super().get_outputs(include_bytecode=include_bytecode)
            + self.mo_outputs
        )


def build():
    """Main function that runs the compilation."""
    distribution = Distribution(
        {
            "package_dir": {"": "src"},
        }
    )
    cmd = Build(distribution)
    cmd.inplace = 1
    cmd.ensure_finalized()
    cmd.run()

    # Copy into src/. This appears to be the thing that actually does all the
    # heavy lifting. I'm not sure why I'm bothering with all the
    # setuptools-specific logic above.
    #
    # In summary: Get .mo files from build directory and put them into
    # src/reuse/locale/{lang}/LC_MESSAGES/reuse.mo.
    for output in cmd.get_outputs():
        relative = Path("src") / os.path.relpath(output, cmd.build_lib)
        relative.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(output, relative)


if __name__ == "__main__":
    build()
