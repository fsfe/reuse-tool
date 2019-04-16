# SPDX-Copyright: 2017-2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Misc. utilities for reuse."""

import logging
import os
import re
import shutil
import subprocess
from gettext import gettext as _
from hashlib import sha1
from pathlib import Path
from typing import BinaryIO, List, Optional, Set, Union

from debian.copyright import Copyright
from license_expression import ExpressionError, Licensing
from spdx.checksum import Algorithm

from . import SpdxInfo

GIT_EXE = shutil.which("git")

_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name
_LICENSING = Licensing()

PathLike = Union[Path, str]  # pylint: disable=invalid-name

_END_PATTERN = r"(?:\*/)*(?:-->)*$"
_IDENTIFIER_PATTERN = re.compile(
    r"SPDX" "-License-Identifier: (.*?)" + _END_PATTERN, re.MULTILINE
)
_COPYRIGHT_PATTERN = re.compile(
    r"SPDX" "-Copyright: (.*?)" + _END_PATTERN, re.MULTILINE
)
_VALID_LICENSE_PATTERN = re.compile(
    r"Valid" "-License-Identifier: (.*?)" + _END_PATTERN, re.MULTILINE
)

# Amount of bytes that we assume will be big enough to contain the entire
# comment header (including SPDX tags), so that we don't need to read the
# entire file.
_HEADER_BYTES = 4096


def setup_logging(level: int = logging.WARNING) -> None:
    """Configure logging for reuse."""
    # library_logger is the root logger for reuse.  We configure logging solely
    # for reuse, not for any other libraries.
    library_logger = logging.getLogger("reuse")
    library_logger.setLevel(level)

    if not library_logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        library_logger.addHandler(handler)


def execute_command(
    command: List[str], logger: logging.Logger, **kwargs
) -> subprocess.CompletedProcess:
    """Run the given command with subprocess.run.  Forward kwargs.  Silence
    output into a pipe unless kwargs override it.
    """
    logger.debug("running %s", " ".join(command))

    stdout = kwargs.get("stdout", subprocess.PIPE)
    stderr = kwargs.get("stderr", subprocess.PIPE)

    return subprocess.run(command, stdout=stdout, stderr=stderr, **kwargs)


def find_root() -> Optional[Path]:
    """Try to find the root of the project from $PWD.  If none is found, return
    None.
    """
    cwd = Path.cwd()
    if in_git_repo(cwd):
        command = [GIT_EXE, "rev-parse", "--show-toplevel"]
        result = execute_command(command, _logger, cwd=str(cwd))

        if not result.returncode:
            path = result.stdout.decode("utf-8")[:-1]
            return Path(os.path.relpath(path, str(cwd)))
    return None


def in_git_repo(cwd: PathLike = None) -> bool:
    """Is *cwd* inside of a git repository?

    Always return False if git is not installed.
    """
    if cwd is None:
        cwd = Path.cwd()

    if GIT_EXE:
        command = [GIT_EXE, "status"]
        result = execute_command(command, _logger, cwd=str(cwd))

        return not result.returncode

    return False


def _all_files_ignored_by_git(root: PathLike) -> Set[str]:
    """Return a set of all files ignored by git. If a whole directory is
    ignored, don't return all files inside of it.

    Return an empty list if git is not installed.
    """
    root = Path(root)

    if GIT_EXE:
        command = [
            GIT_EXE,
            "ls-files",
            "--exclude-standard",
            "--ignored",
            "--others",
            "--directory",
        ]
        result = execute_command(command, _logger, cwd=str(root))
        all_files = result.stdout.decode("utf-8").split("\n")
        return set(all_files)
    return set()


def decoded_text_from_binary(binary_file: BinaryIO, size: int = None) -> str:
    """Given a binary file object, detect its encoding and return its contents
    as a decoded string.  Do not throw any errors if the encoding contains
    errors:  Just replace the false characters.

    If *size* is specified, only read so many bytes.
    """
    rawdata = binary_file.read(size)
    return rawdata.decode("utf-8", errors="replace")


def _determine_license_path(path: PathLike) -> Path:
    """Given a path FILE, return FILE.license if it exists, otherwise return
    FILE.
    """
    path = Path(path)
    license_path = Path("{}.license".format(path))
    if not license_path.exists():
        license_path = path
    return license_path


def _copyright_from_dep5(path: PathLike, copyright: Copyright) -> SpdxInfo:
    """Find the reuse information of *path* in the dep5 Copyright object."""
    result = copyright.find_files_paragraph(str(path))

    if result is None:
        return SpdxInfo(set(), set())

    return SpdxInfo(
        set(map(_LICENSING.parse, [result.license.synopsis])),
        set(map(str.strip, result.copyright.splitlines())),
    )


def extract_spdx_info(text: str) -> None:
    """Extract SPDX information from comments in a string."""
    expression_matches = set(map(str.strip, _IDENTIFIER_PATTERN.findall(text)))
    expressions = set()
    for expression in expression_matches:
        try:
            expressions.add(_LICENSING.parse(expression))
        except ExpressionError:
            _logger.error(_("Could not parse '%s'"), expression)
            raise
    copyright_matches = set(map(str.strip, _COPYRIGHT_PATTERN.findall(text)))

    return SpdxInfo(expressions, copyright_matches)


def extract_valid_license(text: str) -> Set[str]:
    """Extract SPDX identifier from a string."""
    return set(map(str.strip, _VALID_LICENSE_PATTERN.findall(text)))


def _checksum(path: PathLike) -> Algorithm:
    path = Path(path)

    file_sha1 = sha1()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(128 * file_sha1.block_size), b""):
            file_sha1.update(chunk)

    return Algorithm("SHA1", file_sha1.hexdigest())
