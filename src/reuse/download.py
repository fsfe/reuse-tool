# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2023 Nico Rikken <nico.rikken@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Functions for downloading license files from spdx/license-list-data."""

import errno
import logging
import os
import shutil
import urllib.request
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urljoin

from ._licenses import ALL_NON_DEPRECATED_MAP
from ._util import find_licenses_directory
from .extract import _LICENSEREF_PATTERN
from .project import Project
from .types import StrPath
from .vcs import VCSStrategyNone

_LOGGER = logging.getLogger(__name__)

# All raw text files are available as files underneath this path.
_SPDX_REPOSITORY_BASE_URL = (
    "https://raw.githubusercontent.com/spdx/license-list-data/master/text/"
)


def download_license(spdx_identifier: str) -> str:
    """Download the license text from the SPDX repository.

    Args:
        spdx_identifier: SPDX identifier of the license.

    Raises:
        URLError: if the license could not be downloaded.

    Returns:
        The license text.
    """
    if spdx_identifier not in ALL_NON_DEPRECATED_MAP:
        spdx_identifier = f"deprecated_{spdx_identifier}"
    # This is fairly naive, but I can't see anything wrong with it.
    url = urljoin(_SPDX_REPOSITORY_BASE_URL, "".join((spdx_identifier, ".txt")))
    _LOGGER.debug("downloading license from '%s'", url)
    # TODO: Cache result?
    with urllib.request.urlopen(url) as response:
        if response.getcode() == 200:
            return response.read().decode("utf-8")
    raise URLError("Status code was not 200")


def _path_to_license_file(spdx_identifier: str, project: Project) -> Path:
    root: Path | None = project.root
    # Hack
    if (
        root
        and root.name == "LICENSES"
        and isinstance(project.vcs_strategy, VCSStrategyNone)
    ):
        root = None

    licenses_path = find_licenses_directory(root=root)
    return licenses_path / "".join((spdx_identifier, ".txt"))


def put_license_in_file(
    spdx_identifier: str,
    destination: StrPath,
    source: StrPath | None = None,
) -> None:
    """Download a license and put it in the destination file.

    This function exists solely for convenience.

    Args:
        spdx_identifier: SPDX License Identifier of the license.
        destination: Where to put the license.
        source: Path to file or directory containing the text for LicenseRef
            licenses.

    Raises:
        URLError: if the license could not be downloaded.
        FileExistsError: if the license file already exists.
        FileNotFoundError: if the source could not be found in the directory.
    """
    header = ""
    destination = Path(destination)
    destination.parent.mkdir(exist_ok=True)

    if destination.exists():
        raise FileExistsError(
            errno.EEXIST, os.strerror(errno.EEXIST), str(destination)
        )

    # LicenseRef- license; don't download anything.
    if _LICENSEREF_PATTERN.match(spdx_identifier):
        if source:
            source = Path(source)
            if source.is_dir():
                source = source / f"{spdx_identifier}.txt"
            if not source.exists():
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), str(source)
                )
            shutil.copyfile(source, destination)
        else:
            destination.touch()
    else:
        text = download_license(spdx_identifier)
        with destination.open("w", encoding="utf-8") as fp:
            fp.write(header)
            fp.write(text)
