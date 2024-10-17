# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All exceptions owned by :mod:`reuse`. These exceptions all inherit
:class:`ReuseError`.
"""

from typing import Any, Optional


class ReuseError(Exception):
    """Base exception."""


class SpdxIdentifierNotFoundError(ReuseError):
    """Could not find SPDX identifier for license file."""


class GlobalLicensingParseError(ReuseError):
    """An exception representing any kind of error that occurs when trying to
    parse a :class:`reuse.global_licensing.GlobalLicensing` file.
    """

    def __init__(self, *args: Any, source: Optional[str] = None):
        super().__init__(*args)
        self.source = source


class GlobalLicensingParseTypeError(GlobalLicensingParseError, TypeError):
    """An exception representing a type error while trying to parse a
    :class:`reuse.global_licensing.GlobalLicensing` file.
    """


class GlobalLicensingParseValueError(GlobalLicensingParseError, ValueError):
    """An exception representing a value error while trying to parse a
    :class:`reuse.global_licensing.GlobalLicensing` file.
    """


class GlobalLicensingConflictError(ReuseError):
    """There are two global licensing files in the project that are not
    compatible.
    """


class MissingReuseInfoError(ReuseError):
    """Some REUSE information is missing from the result."""


class CommentError(ReuseError):
    """An error occurred during an interaction with a comment."""


class CommentCreateError(Exception):
    """An error occurred during the creation of a comment."""


class CommentParseError(Exception):
    """An error occurred during the parsing of a comment."""
