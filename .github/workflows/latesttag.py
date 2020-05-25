# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import subprocess
from distutils.version import LooseVersion
from urllib.request import urlopen

from packaging.version import parse

from reuse import __version__ as current


def main():
    data = json.loads(
        urlopen("https://pypi.python.org/pypi/reuse/json")
        .read()
        .decode("utf-8")
    )
    latest = max(
        LooseVersion(release)
        for release in data["releases"]
        if not parse(release).is_prerelease
    )

    print(f"Latest stable version on PyPI is '{latest}'")
    print(f"Version in this revision is '{current}'")

    assert str(latest) == current


if __name__ == "__main__":
    main()
