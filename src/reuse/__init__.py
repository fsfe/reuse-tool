# SPDX-FileCopyrightText: 2017-2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""reuse is a tool for compliance with the REUSE recommendations."""

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

from boolean.boolean import Expression
from debian.copyright import Copyright, NotMachineReadableError

_LOGGER = logging.getLogger(__name__)

_PACKAGE_PATH = os.path.dirname(__file__)
_LOCALE_DIR = os.path.join(_PACKAGE_PATH, "locale")

if gettext.find("reuse", localedir=_LOCALE_DIR):
    gettext.bindtextdomain("reuse", _LOCALE_DIR)
    gettext.textdomain("reuse")
    _LOGGER.debug("translations found at %s", _LOCALE_DIR)
else:
    _LOGGER.debug("no translations found at %s", _LOCALE_DIR)

__author__ = "Carmen Bianca Bakker"
__email__ = "carmenbianca@fsfe.org"
__license__ = "GPL-3.0-or-later"
__version__ = "0.5.2"
__REUSE_version__ = "3.0"


_IGNORE_DIR_PATTERNS = [
    re.compile(r"^\.git$"),
    re.compile(r"^LICENSES$"),
    re.compile(r"^\.reuse$"),
]

_IGNORE_FILE_PATTERNS = [
    re.compile(r"^LICENSE"),
    re.compile(r"^COPYING"),
    # ".git" as file happens in submodules
    re.compile(r"^\.git$"),
    re.compile(r"^\.gitkeep$"),
    re.compile(r".*\.license$"),
    re.compile(r".*\.spdx$"),
]

#: Simple structure for holding SPDX information.
#:
#: The two iterables MUST be sets.
SpdxInfo = NamedTuple(
    "SpdxInfo",
    [("spdx_expressions", Set[Expression]), ("copyright_lines", Set[str])],
)


class ReuseException(Exception):
    """Base exception."""


class IdentifierNotFound(ReuseException):
    """Could not find SPDX identifier for license file."""
