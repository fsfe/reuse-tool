# SPDX-Copyright: 2017-2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""reuse is a tool for compliance with the REUSE Initiative recommendations."""

# pylint: disable=ungrouped-imports,too-many-arguments

import contextlib
import datetime
import gettext
import glob
import hashlib
import logging
import os
import re
import sys
from gettext import gettext as _
from pathlib import Path
from typing import (
    BinaryIO,
    Dict,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Set,
    Union,
)
from uuid import uuid4

import pkg_resources
from boolean.boolean import Expression
from debian.copyright import Copyright, NotMachineReadableError

_LOCALE_DIRS = [
    # sys.prefix is usually /usr, but can also be the root of the virtualenv.
    sys.prefix + "/share/locale",
    # Relevant for `pip install --user` installations.
    str(Path.home()) + "/.local/share/locale",
]

try:
    # This somehow works for egg installations.
    _LOCALE_DIRS.append(
        pkg_resources.resource_filename(
            pkg_resources.Requirement.parse("fsfe-reuse"), "share/locale"
        )
    )
except pkg_resources.DistributionNotFound:
    pass

for dir in _LOCALE_DIRS:
    if gettext.find("reuse", localedir=dir):
        gettext.bindtextdomain("reuse", dir)
        gettext.textdomain("reuse")
        break

__author__ = "Carmen Bianca Bakker"
__email__ = "carmenbianca@fsfe.org"
__license__ = "GPL-3.0-or-later"
__version__ = "0.4.0a1"

_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

_IGNORE_DIR_PATTERNS = [
    re.compile(r"^\.git$"),
    re.compile(r"^LICENSES$"),
    re.compile(r"^\.reuse$"),
]

_IGNORE_FILE_PATTERNS = [
    re.compile(r"^LICENSE"),
    re.compile(r"^COPYING"),
    re.compile(r".*\.license$"),
    re.compile(r".*\.spdx$"),
]

#: Simple structure for holding SPDX information.
SpdxInfo = NamedTuple(
    "SpdxInfo",
    [("spdx_expressions", Set[Expression]), ("copyright_lines", Set[str])],
)


class ReuseException(Exception):
    """Base exception."""


class IdentifierNotFound(ReuseException):
    """Could not find SPDX identifier for license file."""
