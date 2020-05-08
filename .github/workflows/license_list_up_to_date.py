# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""A simple script that checks whether the license lists in reuse are
up-to-date.

For convenience, also overwrite the files.
"""

from pathlib import Path

import requests

URLS = {
    "exceptions.json": "https://raw.githubusercontent.com/spdx/license-list-data/master/json/exceptions.json",
    "licenses.json": "https://raw.githubusercontent.com/spdx/license-list-data/master/json/licenses.json",
}


def main():
    result = 0
    for file_, url in URLS.items():
        path = Path(f"src/reuse/resources/{file_}")
        contents = path.read_text()

        response = requests.get(url)
        if response.status_code == 200:
            if response.text == contents:
                print(f"{file_} is up-to-date")
            else:
                result = 1
                print(f"{file_} is not up-to-date")
                path.write_text(response.text)
        else:
            result = 1
            print(f"could not download {file_}")
    return result


if __name__ == "__main__":
    main()
