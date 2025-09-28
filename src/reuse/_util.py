# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2020 Tuomas Siipola <tuomas@zpl.fi>
# SPDX-FileCopyrightText: 2022 Carmen Bianca Bakker <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2022 Nico Rikken <nico.rikken@fsfe.org>
# SPDX-FileCopyrightText: 2022 Pietro Albini <pietro.albini@ferrous-systems.com>
# SPDX-FileCopyrightText: 2023 DB Systel GmbH
# SPDX-FileCopyrightText: 2023 Johannes Zarl-Zierl <johannes@zarl-zierl.at>
# SPDX-FileCopyrightText: 2024 Rivos Inc.
# SPDX-FileCopyrightText: 2024 Skyler Grey <sky@a.starrysky.fyi>
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Misc. utilities for reuse."""

import logging
import os
import subprocess
from hashlib import sha1
from inspect import cleandoc
from pathlib import Path
from typing import IO, Any

from .types import StrPath

# REUSE-IgnoreStart


def setup_logging(level: int = logging.WARNING) -> None:
    """Configure logging for reuse.

    You can only call this function once.
    """
    # library_logger is the root logger for reuse. We configure logging solely
    # for reuse, not for any other libraries.
    library_logger = logging.getLogger("reuse")

    if not library_logger.hasHandlers():
        library_logger.setLevel(level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        library_logger.addHandler(handler)


def execute_command(
    command: list[str],
    logger: logging.Logger,
    cwd: StrPath | None = None,
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    """Run the given command with subprocess.run. Forward kwargs. Silence
    output into a pipe unless kwargs override it.
    """
    logger.debug("running '%s'", " ".join(command))

    stdout: None | int | IO[Any] = kwargs.get("stdout", subprocess.PIPE)
    stderr: None | int | IO[Any] = kwargs.get("stderr", subprocess.PIPE)

    return subprocess.run(
        list(map(str, command)),
        stdout=stdout,
        stderr=stderr,
        check=False,
        cwd=str(cwd),
        **kwargs,
    )


def find_licenses_directory(root: StrPath | None = None) -> Path:
    """Find the licenses directory from CWD or *root*. In the following order:

    - LICENSES/ in *root*.

    - Current directory if its name is "LICENSES"

    - LICENSES/ in CWD.

    The returned LICENSES/ directory NEED NOT EXIST. It may still need to be
    created.
    """
    cwd = Path.cwd()
    licenses_path = cwd / "LICENSES"

    if root:
        licenses_path = Path(root) / "LICENSES"
    elif cwd.name == "LICENSES":
        licenses_path = cwd

    return licenses_path


def _determine_license_path(path: StrPath) -> Path:
    """Given a path FILE, return FILE.license if it exists, otherwise return
    FILE.
    """
    license_path = Path(f"{path}.license")
    if not license_path.exists():
        license_path = Path(path)
    return license_path


def _determine_license_suffix_path(path: StrPath) -> Path:
    """Given a path FILE or FILE.license, return FILE.license."""
    path = Path(path)
    if path.suffix == ".license":
        return path
    return Path(f"{path}.license")


def _strip_plus_from_identifier(spdx_identifier: str) -> str:
    """Strip final plus from identifier.

    >>> _strip_plus_from_identifier("EUPL-1.2+")
    'EUPL-1.2'
    >>> _strip_plus_from_identifier("EUPL-1.2")
    'EUPL-1.2'
    """
    if spdx_identifier.endswith("+"):
        return spdx_identifier[:-1]
    return spdx_identifier


def _add_plus_to_identifier(spdx_identifier: str) -> str:
    """Add final plus to identifier.

    >>> _add_plus_to_identifier("EUPL-1.2")
    'EUPL-1.2+'
    >>> _add_plus_to_identifier("EUPL-1.2+")
    'EUPL-1.2+'
    """
    if spdx_identifier.endswith("+"):
        return spdx_identifier
    return f"{spdx_identifier}+"


def relative_from_root(path: Path, root: Path) -> Path:
    """A helper function to get *path* relative to *root*."""
    path_parts = path.parts
    root_parts = root.parts
    root_parts_len = len(root_parts)

    # This is rather strangely more performant than `path.relative_to(root)`.
    if path_parts[:root_parts_len] == root_parts:
        return Path(*path_parts[root_parts_len:])
    return Path(os.path.relpath(str(path), start=str(root)))


def _checksum(path: StrPath) -> str:
    path = Path(path)

    file_sha1 = sha1()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(128 * file_sha1.block_size), b""):
            file_sha1.update(chunk)

    return file_sha1.hexdigest()


def cleandoc_nl(text: str) -> str:
    """Like :func:`inspect.cleandoc`, but with a newline at the end."""
    return cleandoc(text) + "\n"


# REUSE-IgnoreEnd
