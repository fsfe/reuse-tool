# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Some typing definitions."""

from os import PathLike
from typing import Union

#: Something that looks like a path.
StrPath = Union[str, PathLike[str]]
