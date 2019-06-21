# SPDX-Copyright: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Functions for downloading license files from spdx/license-data-list."""

import errno
import sys
from gettext import gettext as _
from itertools import chain
from os import PathLike
from pathlib import Path
from urllib.parse import urljoin

import requests

from ._licenses import EXCEPTION_MAP, LICENSE_MAP
from ._util import PathType, find_licenses_directory

# All raw text files are available as files underneath this path.
_SPDX_REPOSITORY_BASE_URL = (
    "https://raw.githubusercontent.com/spdx/license-list-data/master/text/"
)


def download_license(spdx_identifier: str) -> str:
    """Download the license text from the SPDX repository.

    :param spdx_identifier: SPDX identifier of the license.
    :raises requests.RequestException: if the license could not be downloaded.
    :return: The license text.
    """
    # This is fairly naive, but I can't see anything wrong with it.
    url = urljoin(
        _SPDX_REPOSITORY_BASE_URL, "".join((spdx_identifier, ".txt"))
    )
    # TODO: Cache result?
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    raise requests.RequestException("Status code was not 200")


def put_license_in_file(
    spdx_identifier: str, root: PathLike = None, destination: PathLike = None
) -> None:
    """Download a license and put it in the correct file.

    This function exists solely for convenience.

    :param spdx_identifier: SPDX identifier of the license.
    :param root: The root of the project.
    :param destination: An override path for the destination of the license.
    :raises requests.RequestException: if the license could not be downloaded.
    :raises FileExistsError: if the license file already exists.
    """
    header = ""
    if destination is None:
        licenses_path = find_licenses_directory(root=root)
        licenses_path.mkdir(exist_ok=True)
        destination = licenses_path / "".join((spdx_identifier, ".txt"))

    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(errno.EEXIST, "File exists", str(destination))

    text = download_license(spdx_identifier)
    with destination.open("w") as fp:
        fp.write(header)
        fp.write(text)


def add_arguments(parser) -> None:
    """Add arguments to parser."""
    parser.add_argument(
        "license", action="store", help=_("SPDX Identifier of license")
    )
    parser.add_argument("--output", "-o", action="store", type=PathType("w"))


def run(args, out=sys.stdout) -> int:
    """Download license and place it in the LICENSES/ directory."""
    destination = None
    if args.output:
        destination = args.output

    try:
        # IMPORTANT: These redundant lines exist SOLELY to make testing not an
        # absolute hell.
        if destination is not None:
            put_license_in_file(args.license, destination=destination)
        else:
            put_license_in_file(args.license)
    except FileExistsError as err:
        out.write(
            _("Error: {} already exists.\n".format(Path(err.filename).name))
        )
        return 1
    except requests.RequestException:
        out.write(_("Error: Failed to download license.\n"))
        if args.license not in chain(LICENSE_MAP, EXCEPTION_MAP):
            out.write(
                _("{} is not a valid SPDX identifier.\n").format(args.license)
            )
        else:
            out.write(_("Is your internet connection working?\n"))
        return 1

    out.write(
        _("Successfully downloaded {spdx_identifier}.").format(
            spdx_identifier=args.license
        )
    )
    return 0
