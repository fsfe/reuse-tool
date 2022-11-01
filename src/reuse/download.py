# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Functions for downloading license files from spdx/license-data-list."""

import errno
import logging
import sys
import urllib.request
from gettext import gettext as _
from os import PathLike
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urljoin

from ._licenses import ALL_NON_DEPRECATED_MAP
from ._util import (
    PathType,
    find_licenses_directory,
    print_incorrect_spdx_identifier,
)
from .project import Project
from .report import ProjectReport

_LOGGER = logging.getLogger(__name__)

# All raw text files are available as files underneath this path.
_SPDX_REPOSITORY_BASE_URL = (
    "https://raw.githubusercontent.com/spdx/license-list-data/master/text/"
)


def download_license(spdx_identifier: str) -> str:
    """Download the license text from the SPDX repository.

    :param spdx_identifier: SPDX identifier of the license.
    :raises URLError: if the license could not be downloaded.
    :return: The license text.
    """
    # This is fairly naive, but I can't see anything wrong with it.
    url = urljoin(_SPDX_REPOSITORY_BASE_URL, "".join((spdx_identifier, ".txt")))
    # TODO: Cache result?
    with urllib.request.urlopen(url) as response:
        if response.getcode() == 200:
            return response.read().decode("utf-8")
    raise URLError("Status code was not 200")


def _path_to_license_file(spdx_identifier: str, root: PathLike) -> Path:
    licenses_path = find_licenses_directory(root=root)
    return licenses_path / "".join((spdx_identifier, ".txt"))


def put_license_in_file(spdx_identifier: str, destination: PathLike) -> None:
    """Download a license and put it in the destination file.

    This function exists solely for convenience.

    :param spdx_identifier: SPDX License Identifier of the license.
    :param destination: Where to put the license.
    :raises URLError: if the license could not be downloaded.
    :raises FileExistsError: if the license file already exists.
    """
    header = ""
    destination = Path(destination)
    destination.parent.mkdir(exist_ok=True)

    if destination.exists():
        raise FileExistsError(errno.EEXIST, "File exists", str(destination))

    text = download_license(spdx_identifier)
    with destination.open("w", encoding="utf-8") as fp:
        fp.write(header)
        fp.write(text)


def add_arguments(parser) -> None:
    """Add arguments to parser."""
    parser.add_argument(
        "license",
        action="store",
        nargs="*",
        help=_("SPDX License Identifier of license"),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help=_("download all missing licenses detected in the project"),
    )
    parser.add_argument(
        "--output", "-o", dest="file", action="store", type=PathType("w")
    )


def run(args, project: Project, out=sys.stdout) -> int:
    """Download license and place it in the LICENSES/ directory."""

    def _already_exists(path: PathLike):
        out.write(
            _("Error: {spdx_identifier} already exists.").format(
                spdx_identifier=path
            )
        )
        out.write("\n")

    def _could_not_download(identifier: str):
        out.write(_("Error: Failed to download license."))
        out.write(" ")
        if identifier not in ALL_NON_DEPRECATED_MAP:
            print_incorrect_spdx_identifier(identifier, out=out)
        else:
            out.write(_("Is your internet connection working?"))
        out.write("\n")

    def _successfully_downloaded(destination: PathLike):
        out.write(
            _("Successfully downloaded {spdx_identifier}.").format(
                spdx_identifier=destination
            )
        )
        out.write("\n")

    if args.all:
        # TODO: This is fairly inefficient, but gets the job done.
        report = ProjectReport.generate(project)
        licenses = report.missing_licenses
        if args.file:
            _LOGGER.warning(
                _("--output has no effect when used together with --all")
            )
            args.file = None
    elif not args.license:
        args.parser.error(_("the following arguments are required: license"))
    elif len(args.license) > 1 and args.file:
        args.parser.error(_("cannot use --output with more than one license"))
    else:
        licenses = args.license

    return_code = 0
    for lic in licenses:
        if args.file:
            destination = args.file
        else:
            destination = _path_to_license_file(lic, project.root)
        try:
            put_license_in_file(lic, destination=destination)
        except URLError:
            _could_not_download(lic)
            return_code = 1
        except FileExistsError as err:
            _already_exists(err.filename)
            return_code = 1
        else:
            _successfully_downloaded(destination)
    return return_code
