# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""reuse is a tool for compliance with the REUSE recommendations."""

import gettext
import logging
import os
import re
from typing import NamedTuple, Set

from boolean.boolean import Expression
from pkg_resources import DistributionNotFound, get_distribution

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    __version__ = "0.12.1"

__author__ = "Carmen Bianca Bakker"
__email__ = "carmenbianca@fsfe.org"
__license__ = "GPL-3.0-or-later"
__REUSE_version__ = "3.0"

_LOGGER = logging.getLogger(__name__)

_PACKAGE_PATH = os.path.dirname(__file__)
_LOCALE_DIR = os.path.join(_PACKAGE_PATH, "locale")

if gettext.find("reuse", localedir=_LOCALE_DIR):
    gettext.bindtextdomain("reuse", _LOCALE_DIR)
    gettext.textdomain("reuse")
    _LOGGER.debug("translations found at %s", _LOCALE_DIR)
else:
    _LOGGER.debug("no translations found at %s", _LOCALE_DIR)


_IGNORE_DIR_PATTERNS = [
    re.compile(r"^\.git$"),
    re.compile(r"^\.hg$"),
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
    # Workaround for https://github.com/fsfe/reuse-tool/issues/229
    re.compile(r"^CAL-1.0(-Combined-Work-Exception)?(\..+)?$"),
    re.compile(r"^SHL-2.1(\..+)?$"),
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
