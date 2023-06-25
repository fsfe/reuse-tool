# SPDX-FileCopyrightText: 2023 Matthias Riße
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""This module adds compatibility code like backports."""
import os
import sys
from pathlib import Path

# Introduce an implementation of pathlib.Path's is_relative_to in python
# versions before 3.9
if sys.version_info < (3, 9):

    def _is_relative_to(self: Path, path: Path) -> bool:
        try:
            self.relative_to(path)
            return True
        except ValueError:
            return False

    setattr(Path, "is_relative_to", _is_relative_to)

# Introduce an implementation of pathlib.Path's readlink in python versions
# before 3.9
if sys.version_info < (3, 9):

    def _readlink(self: Path) -> Path:
        return Path(os.readlink(self))

    setattr(Path, "readlink", _readlink)
