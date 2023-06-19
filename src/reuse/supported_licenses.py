# SPDX-FileCopyrightText: 2021 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""supported-licenses command handler"""

import sys
from argparse import ArgumentParser, Namespace
from typing import IO

from ._licenses import _LICENSES, _load_license_list
from .project import Project


# pylint: disable=unused-argument
def add_arguments(parser: ArgumentParser) -> None:
    """Add arguments to the parser."""


# pylint: disable=unused-argument
def run(args: Namespace, project: Project, out: IO[str] = sys.stdout) -> int:
    """Print the supported SPDX licenses list"""

    licenses = _load_license_list(_LICENSES)[1]

    for license_id, license_info in licenses.items():
        license_name = license_info["name"]
        license_reference = license_info["reference"]
        out.write(
            f"{license_id: <40}\t{license_name: <80}\t"
            f"{license_reference: <50}\n"
        )

    return 0
