# SPDX-FileCopyrightText: 2021 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""supported-licenses command handler"""

import sys

from ._licenses import _LICENSES, _load_license_list
from .project import Project

# pylint: disable=unused-argument


def add_arguments(parser) -> None:
    """Add arguments to the parser."""


def run(args, project: Project, out=sys.stdout):
    """Print the supported SPDX licenses list"""

    licenses = _load_license_list(_LICENSES)[1]

    for license_id, license_info in licenses.items():
        license_name = license_info["name"]
        license_reference = license_info["reference"]
        out.write(
            "{: <40}\t{: <80}\t{: <50}\n".format(
                license_id, license_name, license_reference
            )
        )

    return 0
