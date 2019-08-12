# SPDX-FileCopyrightText: 2017-2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Misc. utilities for reuse."""

# pylint: disable=ungrouped-imports

import logging
import os
import re
import shutil
import subprocess
from argparse import ArgumentTypeError
from gettext import gettext as _
from hashlib import sha1
from os import PathLike
from pathlib import Path
from typing import BinaryIO, List, Optional, Set

from boolean.boolean import Expression, ParseError
from debian.copyright import Copyright
from license_expression import ExpressionError, Licensing

from . import SpdxInfo

GIT_EXE = shutil.which("git")

_LOGGER = logging.getLogger(__name__)
_LICENSING = Licensing()

_END_PATTERN = r"(?:\*/)*(?:-->)*$"
_IDENTIFIER_PATTERN = re.compile(
    r"SPDX" "-License-Identifier: (.*?)" + _END_PATTERN, re.MULTILINE
)
_COPYRIGHT_PATTERNS = [
    re.compile(r"(SPDX" "-FileCopyrightText: .*?)" + _END_PATTERN),
    re.compile(r"(Copyright .*?)" + _END_PATTERN),
    re.compile(r"(© .*?)" + _END_PATTERN),
]

# Amount of bytes that we assume will be big enough to contain the entire
# comment header (including SPDX tags), so that we don't need to read the
# entire file.
_HEADER_BYTES = 4096


def setup_logging(level: int = logging.WARNING) -> None:
    """Configure logging for reuse."""
    # library_logger is the root logger for reuse. We configure logging solely
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
    """Run the given command with subprocess.run. Forward kwargs. Silence
    output into a pipe unless kwargs override it.
    """
    logger.debug("running %s", " ".join(command))

    stdout = kwargs.get("stdout", subprocess.PIPE)
    stderr = kwargs.get("stderr", subprocess.PIPE)

    return subprocess.run(command, stdout=stdout, stderr=stderr, **kwargs)


def find_root() -> Optional[Path]:
    """Try to find the root of the project from CWD. If none is found, return
    None.
    """
    cwd = Path.cwd()
    if in_git_repo(cwd):
        command = [GIT_EXE, "rev-parse", "--show-toplevel"]
        result = execute_command(command, _LOGGER, cwd=cwd)

        if not result.returncode:
            path = result.stdout.decode("utf-8")[:-1]
            return Path(os.path.relpath(path, cwd))
    return None


def find_licenses_directory(root: PathLike = None) -> Optional[Path]:
    """Find the licenses directory from CWD or *root*. In the following order:

    - LICENSES/ in *root*.

    - Current directory if its name is "LICENSES"

    - LICENSES/ in CWD.

    The returned LICENSES/ directory NEED NOT EXIST. It may still need to be
    created.
    """
    if root is None:
        root = find_root()
    cwd = Path.cwd()
    licenses_path = cwd / "LICENSES"

    if root:
        licenses_path = root / "LICENSES"
    elif cwd.name == "LICENSES":
        licenses_path = cwd

    return licenses_path


def in_git_repo(cwd: PathLike = None) -> bool:
    """Is *cwd* inside of a git repository?

    Always return False if git is not installed.
    """
    if cwd is None:
        cwd = Path.cwd()

    if GIT_EXE:
        command = [GIT_EXE, "status"]
        result = execute_command(command, _LOGGER, cwd=cwd)

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
            # TODO: This flag is unexpected.  I reported it as a bug in Git.
            # This flag---counter-intuitively---lists untracked directories
            # that contain ignored files.
            "--no-empty-directory",
            # Separate output with \0 instead of \n.
            "-z",
        ]
        result = execute_command(command, _LOGGER, cwd=root)
        all_files = result.stdout.decode("utf-8").split("\0")
        return set(all_files)
    return set()


def decoded_text_from_binary(binary_file: BinaryIO, size: int = None) -> str:
    """Given a binary file object, detect its encoding and return its contents
    as a decoded string. Do not throw any errors if the encoding contains
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
    result = copyright.find_files_paragraph(Path(path).as_posix())

    if result is None:
        return SpdxInfo(set(), set())

    return SpdxInfo(
        set(map(_LICENSING.parse, [result.license.synopsis])),
        set(map(str.strip, result.copyright.splitlines())),
    )


def extract_spdx_info(text: str) -> None:
    """Extract SPDX information from comments in a string.

    :raises ExpressionError: if an SPDX expression could not be parsed
    """
    expression_matches = set(map(str.strip, _IDENTIFIER_PATTERN.findall(text)))
    expressions = set()
    copyright_matches = set()
    for expression in expression_matches:
        try:
            expressions.add(_LICENSING.parse(expression))
        except (ExpressionError, ParseError):
            _LOGGER.error(_("Could not parse '%s'"), expression)
            raise
    for line in text.splitlines():
        for pattern in _COPYRIGHT_PATTERNS:
            match = pattern.search(line)
            if match is not None:
                copyright_matches.add(match.groups()[0])
                break

    return SpdxInfo(expressions, copyright_matches)


def make_copyright_line(statement: str, year: str = None) -> str:
    """Given a statement, prefix it with ``SPDX-FileCopyrightText:`` if it is
    not already prefixed with some manner of copyright tag.
    """
    if "\n" in statement:
        raise RuntimeError(f"Unexpected newline in '{statement}'")
    for pattern in _COPYRIGHT_PATTERNS:
        match = pattern.search(statement)
        if match is not None:
            return statement
    if year is not None:
        return f"SPDX-FileCopyrightText: {year} {statement}"
    return f"SPDX-FileCopyrightText: {statement}"


def _checksum(path: PathLike) -> str:
    path = Path(path)

    file_sha1 = sha1()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(128 * file_sha1.block_size), b""):
            file_sha1.update(chunk)

    return file_sha1.hexdigest()


class PathType:  # pylint: disable=too-few-public-methods
    """Factory for creating Paths"""

    def __init__(self, mode="r", force_file=False, force_directory=False):
        if mode in ("r", "w"):
            self._mode = mode
        else:
            raise ValueError("mode='{}' is not valid".format(mode))
        self._force_file = force_file
        self._force_directory = force_directory
        if self._force_file and self._force_directory:
            raise ValueError(
                "'force_file' and 'force_directory' cannot both be True"
            )

    def __call__(self, string):
        path = Path(string)

        try:
            # pylint: disable=no-else-raise
            if self._mode == "r":
                if path.exists() and os.access(path, os.R_OK):
                    if self._force_file and not path.is_file():
                        raise ArgumentTypeError(
                            _("'{}' is not a file").format(path)
                        )
                    if self._force_directory and not path.is_dir():
                        raise ArgumentTypeError(
                            _("'{}' is not a directory").format(path)
                        )
                    return path
                raise ArgumentTypeError(_("can't open '{}'").format(path))
            else:
                if path.is_dir():
                    raise ArgumentTypeError(
                        _("can't write to directory '{}'").format(path)
                    )
                if path.exists() and os.access(path, os.W_OK):
                    return path
                if not path.exists() and os.access(path.parent, os.W_OK):
                    return path
                raise ArgumentTypeError(_("can't write to '{}'").format(path))
        except OSError:
            raise ArgumentTypeError(_("can't read or write '{}'").format(path))


def spdx_identifier(text: str) -> Expression:
    """argparse factory for creating SPDX expressions."""
    try:
        return _LICENSING.parse(text)
    except (ExpressionError, ParseError):
        raise ArgumentTypeError(
            _("'{}' is not a valid SPDX expression, aborting").format(text)
        )
