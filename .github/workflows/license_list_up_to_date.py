# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""A simple script that checks whether the license lists in reuse are
up-to-date.

For convenience, also overwrite the files.
"""

import json
import sys
import urllib.request
from pathlib import Path

from packaging import version

API_URL = "https://api.github.com/repos/spdx/license-list-data/tags"
URLS = {
    "exceptions.json": "https://raw.githubusercontent.com/spdx/license-list-data/{tag}/json/exceptions.json",
    "licenses.json": "https://raw.githubusercontent.com/spdx/license-list-data/{tag}/json/licenses.json",
}


def latest_tag():
    with urllib.request.urlopen(API_URL) as response:
        contents = response.read().decode("utf-8")
    dictionary = json.loads(contents)
    tags = [item["name"] for item in dictionary]
    sorted_tags = sorted(tags, key=version.parse)
    return sorted_tags[-1]


def main():
    result = 0

    tag = latest_tag()
    print(f"spdx-license-list-data latest version is {tag}")

    for file_, url in URLS.items():
        url = url.format(tag=tag)
        path = Path(f"src/reuse/resources/{file_}")
        local_contents = path.read_text()

        with urllib.request.urlopen(url) as response:
            remote_contents = response.read().decode("utf-8")
        if remote_contents == local_contents:
            print(f"{file_} is up-to-date")
        else:
            result = 1
            print(f"{file_} is not up-to-date")
            path.write_text(remote_contents)
    return result


if __name__ == "__main__":
    sys.exit(main())
