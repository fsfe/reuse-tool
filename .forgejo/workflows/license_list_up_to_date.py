# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""A simple script that checks whether the license lists in reuse are
up-to-date.

For convenience, also overwrite the files.
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

API_URL = "https://api.github.com/repos/spdx/license-list-data/releases/latest"
URLS = {
    # pylint: disable=line-too-long
    "exceptions.json": "https://raw.githubusercontent.com/spdx/license-list-data/{tag}/json/exceptions.json",
    "licenses.json": "https://raw.githubusercontent.com/spdx/license-list-data/{tag}/json/licenses.json",
}


# Fetch arguments
parser = argparse.ArgumentParser(
    description="Check and update included SPDX licenses and exceptions"
)
parser.add_argument(
    "-d",
    "--download",
    action="store_true",
    help="if newer licenses/exceptions are found, download them to the repo",
)
args = parser.parse_args()


def latest_tag():
    """Find out the tag name of latest stable release of the repo"""
    with urllib.request.urlopen(API_URL) as response:
        contents = response.read().decode("utf-8")
    dictionary = json.loads(contents)
    return dictionary["tag_name"]


def main(args_):
    """Compare local and remote files, and download if not matching"""
    result = 0

    tag = latest_tag()
    print(f"spdx-license-list-data latest version is {tag}")

    for file_, url in URLS.items():
        url = url.format(tag=tag)
        path = Path(f"src/reuse/resources/{file_}")
        local_contents = path.read_text(encoding="utf-8")

        with urllib.request.urlopen(url) as response:
            remote_contents = response.read().decode("utf-8")
        if remote_contents == local_contents:
            print(f"{file_} is up-to-date")
        else:
            if args_.download:
                print(f"{file_} is not up-to-date, downloading newer release")
                path.write_text(remote_contents, encoding="utf-8")
            else:
                result = 1
                print(f"{file_} is not up-to-date")

    return result


if __name__ == "__main__":
    sys.exit(main(args))
