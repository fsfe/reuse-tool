# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
# SPDX-FileCopyrightText: 2020 Tuomas Siipola <tuomas@zpl.fi>
# SPDX-FileCopyrightText: 2022 Nico Rikken <nico.rikken@fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2022 Carmen Bianca Bakker <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Misc. utilities for reuse."""


import logging
import os
import re
import shutil
import subprocess
import sys
from argparse import ArgumentTypeError
from difflib import SequenceMatcher
from gettext import gettext as _
from hashlib import sha1
from os import PathLike
from pathlib import Path
from typing import BinaryIO, List, Optional, Set

from boolean.boolean import Expression, ParseError
from debian.copyright import Copyright
from license_expression import ExpressionError, Licensing

from . import SpdxInfo
from ._comment import _all_style_classes
from ._licenses import ALL_NON_DEPRECATED_MAP

GIT_EXE = shutil.which("git")
HG_EXE = shutil.which("hg")

REUSE_IGNORE_START = "REUSE-IgnoreStart"
REUSE_IGNORE_END = "REUSE-IgnoreEnd"

_LOGGER = logging.getLogger(__name__)
_LICENSING = Licensing()

_END_PATTERN = r"{}$".format(  # pylint: disable=consider-using-f-string
    "".join(
        {
            r"(?:{})*".format(  # pylint: disable=consider-using-f-string
                re.escape(style.MULTI_LINE[2])
            )
            for style in _all_style_classes()
            if style.MULTI_LINE[2]
        }
    )
)
_IDENTIFIER_PATTERN = re.compile(
    r"SPDX-License-Identifier:[ \t]+(.*?)" + _END_PATTERN, re.MULTILINE
)
_COPYRIGHT_PATTERNS = [
    re.compile(
        r"(?P<copyright>(?P<prefix>SPDX-FileCopyrightText:)\s+"
        r"((?P<year>\d{4} - \d{4}|\d{4}),?\s+)?"
        r"(?P<statement>.*)?)" + _END_PATTERN
    ),
    re.compile(
        r"(?P<copyright>(?P<prefix>Copyright(\s?\([cC]\))?)\s+"
        r"((?P<year>\d{4} - \d{4}|\d{4}),?\s+)?"
        r"(?P<statement>.*)?)" + _END_PATTERN
    ),
    re.compile(
        r"(?P<copyright>(?P<prefix>©)\s+"
        r"((?P<year>\d{4} - \d{4}|\d{4}),?\s+)?"
        r"(?P<statement>.*)?)" + _END_PATTERN
    ),
    re.compile(
        r"(?P<copyright>(?P<prefix>\([cC]\))\s+"
        r"((?P<year>\d{4} - \d{4}|\d{4}),?\s+)?"
        r"(?P<statement>.*)?)" + _END_PATTERN
    ),
]

_COPYRIGHT_STYLES = {
    # REUSE-IgnoreStart
    "c": "(C)",
    "c-lower": "(c)",
    "spdx": "SPDX-FileCopyrightText:",
    "spdx-symbol": "SPDX-FileCopyrightText: ©",
    "string": "Copyright",
    "string-c": "Copyright (C)",
    "string-symbol": "Copyright ©",
    "symbol": "©",
    # REUSE-IgnoreEnd
}

# Amount of bytes that we assume will be big enough to contain the entire
# comment header (including SPDX tags), so that we don't need to read the
# entire file.
_HEADER_BYTES = 4096


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
    command: List[str], logger: logging.Logger, cwd: PathLike = None, **kwargs
) -> subprocess.CompletedProcess:
    """Run the given command with subprocess.run. Forward kwargs. Silence
    output into a pipe unless kwargs override it.
    """
    logger.debug("running '%s'", " ".join(command))

    stdout = kwargs.get("stdout", subprocess.PIPE)
    stderr = kwargs.get("stderr", subprocess.PIPE)

    return subprocess.run(
        map(str, command),
        stdout=stdout,
        stderr=stderr,
        check=False,
        cwd=str(cwd),
        **kwargs,
    )


def find_licenses_directory(root: PathLike) -> Optional[Path]:
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
        licenses_path = root / "LICENSES"
    elif cwd.name == "LICENSES":
        licenses_path = cwd

    return licenses_path


def decoded_text_from_binary(binary_file: BinaryIO, size: int = None) -> str:
    """Given a binary file object, detect its encoding and return its contents
    as a decoded string. Do not throw any errors if the encoding contains
    errors:  Just replace the false characters.

    If *size* is specified, only read so many bytes.
    """
    rawdata = binary_file.read(size)
    result = rawdata.decode("utf-8", errors="replace")
    return result.replace("\r\n", "\n")


def _determine_license_path(path: PathLike) -> Path:
    """Given a path FILE, return FILE.license if it exists, otherwise return
    FILE.
    """
    license_path = Path(f"{path}.license")
    if not license_path.exists():
        license_path = Path(path)
    return license_path


def _determine_license_suffix_path(path: PathLike) -> Path:
    """Given a path FILE or FILE.license, return FILE.license."""
    path = Path(path)
    if path.suffix == ".license":
        return path
    return Path(f"{path}.license")


def _copyright_from_dep5(path: PathLike, dep5_copyright: Copyright) -> SpdxInfo:
    """Find the reuse information of *path* in the dep5 Copyright object."""
    result = dep5_copyright.find_files_paragraph(Path(path).as_posix())

    if result is None:
        return SpdxInfo(set(), set())

    return SpdxInfo(
        set(map(_LICENSING.parse, [result.license.synopsis])),
        set(map(str.strip, result.copyright.splitlines())),
    )


def _parse_copyright_year(year: str) -> list:
    """Parse copyright years and return list."""
    if not year:
        ret = []
    if re.match(r"\d{4}$", year):
        ret = [int(year)]
    if re.match(r"\d{4} - \d{4}$", year):
        ret = [int(year[:4]), int(year[-4:])]
    return ret


def merge_copyright_lines(copyright_lines: Set[str]) -> Set[str]:
    """Parse all copyright lines and merge identical statements making years
    into a range.
    If a same statement uses multiple prefixes, use only the most frequent one.
    """
    copyright_in = []
    for line in copyright_lines:
        for pattern in _COPYRIGHT_PATTERNS:
            match = pattern.search(line)
            if match is not None:
                copyright_in.append(
                    {
                        "statement": match.groupdict()["statement"],
                        "year": _parse_copyright_year(
                            match.groupdict()["year"]
                        ),
                        "prefix": match.groupdict()["prefix"],
                    }
                )

    copyright_out = []
    for statement in {item["statement"] for item in copyright_in}:
        copyright_list = [
            item for item in copyright_in if item["statement"] == statement
        ]
        prefixes = [item["prefix"] for item in copyright_list]

        # Get the style of the most common prefix
        prefix = max(set(prefixes), key=prefixes.count)
        style = "spdx"
        # pylint: disable=consider-using-dict-items
        for sty in _COPYRIGHT_STYLES:
            if prefix == _COPYRIGHT_STYLES[sty]:
                style = sty
                break

        # get year range if any
        years = []
        for copy in copyright_list:
            years += copy["year"]

        if len(years) == 0:
            year = None
        elif min(years) == max(years):
            year = min(years)
        else:
            year = f"{min(years)} - {max(years)}"

        copyright_out.append(make_copyright_line(statement, year, style))
    return copyright_out


def extract_spdx_info(text: str) -> SpdxInfo:
    """Extract SPDX information from comments in a string.

    :raises ExpressionError: if an SPDX expression could not be parsed
    :raises ParseError: if an SPDX expression could not be parsed
    """
    text = filter_ignore_block(text)
    expression_matches = set(map(str.strip, _IDENTIFIER_PATTERN.findall(text)))
    expressions = set()
    copyright_matches = set()
    for expression in expression_matches:
        try:
            expressions.add(_LICENSING.parse(expression))
        except (ExpressionError, ParseError):
            _LOGGER.error(
                _("Could not parse '{expression}'").format(
                    expression=expression
                )
            )
            raise
    for line in text.splitlines():
        for pattern in _COPYRIGHT_PATTERNS:
            match = pattern.search(line)
            if match is not None:
                copyright_matches.add(match.groupdict()["copyright"])
                break

    return SpdxInfo(expressions, copyright_matches)


def filter_ignore_block(text: str) -> str:
    """Filter out blocks beginning with REUSE_IGNORE_START and ending with
    REUSE_IGNORE_END to remove lines that should not be treated as copyright and
    licensing information.
    """
    ignore_start = None
    ignore_end = None
    if REUSE_IGNORE_START in text:
        ignore_start = text.index(REUSE_IGNORE_START)
    if REUSE_IGNORE_END in text:
        ignore_end = text.index(REUSE_IGNORE_END) + len(REUSE_IGNORE_END)
    if not ignore_start:
        return text
    if not ignore_end:
        return text[:ignore_start]
    if ignore_end > ignore_start:
        return text[:ignore_start] + filter_ignore_block(text[ignore_end:])
    rest = text[ignore_start + len(REUSE_IGNORE_START) :]
    if REUSE_IGNORE_END in rest:
        ignore_end = rest.index(REUSE_IGNORE_END) + len(REUSE_IGNORE_END)
        return text[:ignore_start] + filter_ignore_block(rest[ignore_end:])
    return text[:ignore_start]


def contains_spdx_info(text: str) -> bool:
    """The text contains SPDX info."""
    try:
        return any(extract_spdx_info(text))
    except (ExpressionError, ParseError):
        return False


def make_copyright_line(
    statement: str, year: Optional[str] = None, copyright_style: str = "spdx"
) -> str:
    """Given a statement, prefix it with ``SPDX-FileCopyrightText:`` if it is
    not already prefixed with some manner of copyright tag.
    """
    if "\n" in statement:
        raise RuntimeError(f"Unexpected newline in '{statement}'")

    copyright_prefix = _COPYRIGHT_STYLES.get(copyright_style)
    if copyright_prefix is None:
        raise RuntimeError(
            "Unexpected copyright style: Need 'c', 'c-lower', 'spdx', "
            "'spdx-symbol', 'string', 'string-c', 'string-symbol' or 'symbol'"
        )

    for pattern in _COPYRIGHT_PATTERNS:
        match = pattern.search(statement)
        if match is not None:
            return statement
    if year is not None:
        return f"{copyright_prefix} {year} {statement}"
    return f"{copyright_prefix} {statement}"


def _checksum(path: PathLike) -> str:
    path = Path(path)

    file_sha1 = sha1()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(128 * file_sha1.block_size), b""):
            file_sha1.update(chunk)

    return file_sha1.hexdigest()


class PathType:
    """Factory for creating Paths"""

    def __init__(self, mode="r", force_file=False, force_directory=False):
        if mode in ("r", "r+", "w"):
            self._mode = mode
        else:
            raise ValueError(f"mode='{mode}' is not valid")
        self._force_file = force_file
        self._force_directory = force_directory
        if self._force_file and self._force_directory:
            raise ValueError(
                "'force_file' and 'force_directory' cannot both be True"
            )

    def _check_read(self, path):
        if path.exists() and os.access(path, os.R_OK):
            if self._force_file and not path.is_file():
                raise ArgumentTypeError(_("'{}' is not a file").format(path))
            if self._force_directory and not path.is_dir():
                raise ArgumentTypeError(
                    _("'{}' is not a directory").format(path)
                )
            return
        raise ArgumentTypeError(_("can't open '{}'").format(path))

    def _check_write(self, path):
        # pylint: disable=no-self-use
        if path.is_dir():
            raise ArgumentTypeError(
                _("can't write to directory '{}'").format(path)
            )
        if path.exists() and os.access(path, os.W_OK):
            return
        if not path.exists() and os.access(path.parent, os.W_OK):
            return
        raise ArgumentTypeError(_("can't write to '{}'").format(path))

    def __call__(self, string):
        path = Path(string)

        try:
            if self._mode in ("r", "r+"):
                self._check_read(path)
            if self._mode in ("w", "r+"):
                self._check_write(path)
            return path
        except OSError as error:
            raise ArgumentTypeError(
                _("can't read or write '{}'").format(path)
            ) from error


def spdx_identifier(text: str) -> Expression:
    """argparse factory for creating SPDX expressions."""
    try:
        return _LICENSING.parse(text)
    except (ExpressionError, ParseError) as error:
        raise ArgumentTypeError(
            _("'{}' is not a valid SPDX expression, aborting").format(text)
        ) from error


def similar_spdx_identifiers(identifier: str) -> List[str]:
    """Given an incorrect SPDX identifier, return a list of similar ones."""
    suggestions = []
    if identifier in ALL_NON_DEPRECATED_MAP:
        return suggestions

    for valid_identifier in ALL_NON_DEPRECATED_MAP:
        distance = SequenceMatcher(
            a=identifier.lower(), b=valid_identifier[: len(identifier)].lower()
        ).ratio()
        if distance > 0.75:
            suggestions.append(valid_identifier)
    suggestions = sorted(suggestions)

    return suggestions


def print_incorrect_spdx_identifier(identifier: str, out=sys.stdout) -> None:
    """Print out that *identifier* is not valid, and follow up with some
    suggestions.
    """
    out.write(
        _("'{}' is not a valid SPDX License Identifier.").format(identifier)
    )
    out.write("\n")

    suggestions = similar_spdx_identifiers(identifier)
    if suggestions:
        out.write("\n")
        out.write(_("Did you mean:"))
        out.write("\n")
        for suggestion in suggestions:
            out.write(f"* {suggestion}\n")
        out.write("\n")
    out.write(
        _(
            "See <https://spdx.org/licenses/> for a list of valid "
            "SPDX License Identifiers."
        )
    )


def detect_line_endings(text: str) -> str:
    """Return one of '\n', '\r' or '\r\n' depending on the line endings used in
    *text*. Return os.linesep if there are no line endings.
    """
    line_endings = ["\r\n", "\r", "\n"]
    for line_ending in line_endings:
        if line_ending in text:
            return line_ending
    return os.linesep
