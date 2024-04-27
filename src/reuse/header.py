# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2019 Stefan Bakker <s.bakker777@gmail.com>
# SPDX-FileCopyrightText: 2019 Kirill Elagin <kirelagin@gmail.com>
# SPDX-FileCopyrightText: 2020 Dmitry Bogatov
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
# SPDX-FileCopyrightText: 2021 Alvar Penning
# SPDX-FileCopyrightText: 2021 Alliander N.V. <https://alliander.com>
# SPDX-FileCopyrightText: 2021 Robin Vobruba <hoijui.quaero@gmail.com>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2022 Yaman Qalieh
# SPDX-FileCopyrightText: 2022 Carmen Bianca Bakker <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Functions for manipulating the comment headers of files."""

import logging
import re
from gettext import gettext as _
from typing import NamedTuple, Optional, Sequence, Tuple, Type, cast

from boolean.boolean import ParseError
from jinja2 import Environment, PackageLoader, Template
from license_expression import ExpressionError

from . import ReuseInfo
from ._util import (
    contains_reuse_info,
    extract_reuse_info,
    merge_copyright_lines,
)
from .comment import (
    CommentCreateError,
    CommentParseError,
    CommentStyle,
    EmptyCommentStyle,
    PythonCommentStyle,
)

_LOGGER = logging.getLogger(__name__)

_ENV = Environment(loader=PackageLoader("reuse", "templates"), trim_blocks=True)
DEFAULT_TEMPLATE = _ENV.get_template("default_template.jinja2")

_NEWLINE_PATTERN = re.compile(r"\n", re.MULTILINE)


class _TextSections(NamedTuple):
    """Used to split up text in three parts."""

    before: str
    middle: str
    after: str


class MissingReuseInfo(Exception):
    """Some REUSE information is missing from the result."""


def _create_new_header(
    reuse_info: ReuseInfo,
    template: Optional[Template] = None,
    template_is_commented: bool = False,
    style: Optional[Type[CommentStyle]] = None,
    force_multi: bool = False,
) -> str:
    """Format a new header from scratch.

    Raises:
        CommentCreateError: if a comment could not be created.
        MissingReuseInfo: if the generated comment is missing SPDX information.
    """
    if template is None:
        template = DEFAULT_TEMPLATE
    if style is None:
        style = cast(Type[CommentStyle], PythonCommentStyle)

    rendered = template.render(
        copyright_lines=sorted(reuse_info.copyright_lines),
        contributor_lines=sorted(reuse_info.contributor_lines),
        spdx_expressions=sorted(map(str, reuse_info.spdx_expressions)),
    ).strip("\n")

    if template_is_commented:
        result = rendered
    else:
        result = style.create_comment(rendered, force_multi=force_multi).strip(
            "\n"
        )

    # Verify that the result contains all ReuseInfo.
    new_reuse_info = extract_reuse_info(result)
    if (
        reuse_info.copyright_lines != new_reuse_info.copyright_lines
        and reuse_info.spdx_expressions != new_reuse_info.spdx_expressions
    ):
        _LOGGER.debug(
            _(
                "generated comment is missing copyright lines or license"
                " expressions"
            )
        )
        _LOGGER.debug(result)
        raise MissingReuseInfo()

    return result


# pylint: disable=too-many-arguments
def create_header(
    reuse_info: ReuseInfo,
    header: Optional[str] = None,
    template: Optional[Template] = None,
    template_is_commented: bool = False,
    style: Optional[Type[CommentStyle]] = None,
    force_multi: bool = False,
    merge_copyrights: bool = False,
) -> str:
    """Create a header containing *reuse_info*. *header* is an optional argument
    containing a header which should be modified to include *reuse_info*. If
    *header* is not given, a brand new header is created.

    *template*, *template_is_commented*, and *style* determine what the header
    will look like, and whether it will be commented or not.

    Raises:
        CommentCreateError: if a comment could not be created.
        MissingReuseInfo: if the generated comment is missing SPDX information.
    """
    if template is None:
        template = DEFAULT_TEMPLATE
    if style is None:
        style = PythonCommentStyle

    new_header = ""
    if header:
        try:
            existing_spdx = extract_reuse_info(header)
        except (ExpressionError, ParseError) as err:
            raise CommentCreateError(
                "existing header contains an erroneous SPDX expression"
            ) from err

        if merge_copyrights:
            spdx_copyrights = merge_copyright_lines(
                reuse_info.copyright_lines.union(existing_spdx.copyright_lines),
            )
        else:
            spdx_copyrights = reuse_info.copyright_lines.union(
                existing_spdx.copyright_lines
            )

        # TODO: This behaviour does not match the docstring.
        reuse_info = existing_spdx | reuse_info
        reuse_info = reuse_info.copy(copyright_lines=spdx_copyrights)

    new_header += _create_new_header(
        reuse_info,
        template=template,
        template_is_commented=template_is_commented,
        style=style,
        force_multi=force_multi,
    )
    return new_header


def _indices_of_newlines(text: str) -> Sequence[int]:
    indices = [0]
    start = 0

    while True:
        match = _NEWLINE_PATTERN.search(text, start)
        if match:
            start = match.span()[1]
            indices.append(start)
        else:
            break

    return indices


def _find_first_spdx_comment(
    text: str, style: Optional[Type[CommentStyle]] = None
) -> _TextSections:
    """Find the first SPDX comment in the file. Return a tuple with everything
    preceding the comment, the comment itself, and everything following it.

    Raises:
        MissingReuseInfo: if no REUSE info can be found in any comment
    """
    if style is None:
        style = PythonCommentStyle

    indices = _indices_of_newlines(text)

    for index in indices:
        try:
            comment = style.comment_at_first_character(text[index:])
        except CommentParseError:
            continue
        if contains_reuse_info(comment):
            return _TextSections(
                text[:index], comment + "\n", text[index + len(comment) + 1 :]
            )

    raise MissingReuseInfo()


def _extract_shebang(prefix: str, text: str) -> Tuple[str, str]:
    """Remove all lines that start with the shebang prefix from *text*. Return a
    tuple of (shebang, reduced_text).
    """
    shebang_lines = []
    for line in text.splitlines():
        if line.startswith(prefix):
            shebang_lines.append(line)
            text = text.replace(line, "", 1)
        else:
            break
    shebang = "\n".join(shebang_lines)
    return (shebang, text)


# pylint: disable=too-many-arguments
def find_and_replace_header(
    text: str,
    reuse_info: ReuseInfo,
    template: Optional[Template] = None,
    template_is_commented: bool = False,
    style: Optional[Type[CommentStyle]] = None,
    force_multi: bool = False,
    merge_copyrights: bool = False,
) -> str:
    """Find the first SPDX comment block in *text*. That comment block is
    replaced by a new comment block containing *reuse_info*. It is formatted as
    according to *template*. The template is normally uncommented, but if it is
    already commented, *template_is_commented* should be :const:`True`.

    If both *style* and *template_is_commented* are provided, *style* is only
    used to find the header comment.

    If the comment block already contained some REUSE information, that
    information is merged into *reuse_info*.

    If no header exists, one is simply created.

    *text* is returned with a new header.

    Raises:
        CommentCreateError: if a comment could not be created.
        MissingReuseInfo: if the generated comment is missing SPDX information.
    """
    if style is None:
        style = PythonCommentStyle

    try:
        before, header, after = _find_first_spdx_comment(text, style=style)
    except MissingReuseInfo:
        before, header, after = "", "", text

    # Workaround. EmptyCommentStyle should always be completely replaced.
    if style is EmptyCommentStyle:
        after = ""

    _LOGGER.debug(f"before = {repr(before)}")
    _LOGGER.debug(f"header = {repr(header)}")
    _LOGGER.debug(f"after = {repr(after)}")

    # Keep special first-line-of-file lines as the first line in the file,
    # or say, move our comments after it.
    if style.SHEBANGS:
        for shebang in style.SHEBANGS:
            # Extract shebang from header and put it in before. It's a bit
            # messy, but it ends up working.
            if header.startswith(shebang) and not before.strip():
                before, header = _extract_shebang(shebang, header)
            elif after.startswith(shebang) and not any((before, header)):
                before, after = _extract_shebang(shebang, after)
            else:
                continue
            break

    header = create_header(
        reuse_info,
        header,
        template=template,
        template_is_commented=template_is_commented,
        style=style,
        force_multi=force_multi,
        merge_copyrights=merge_copyrights,
    )

    new_text = f"{header}\n"
    if before.strip():
        new_text = f"{before.rstrip()}\n\n{new_text}"
    if after.strip():
        new_text = f"{new_text}\n{after.lstrip()}"
    return new_text


# pylint: disable=too-many-arguments
def add_new_header(
    text: str,
    reuse_info: ReuseInfo,
    template: Optional[Template] = None,
    template_is_commented: bool = False,
    style: Optional[Type[CommentStyle]] = None,
    force_multi: bool = False,
    merge_copyrights: bool = False,
) -> str:
    """Add a new header at the very top of *text*, similar to
    find_and_replace_header. But in this function, do not replace any headers or
    search for any existing REUSE information.

    Raises:
        CommentCreateError: if a comment could not be created.
    """
    if style is None:
        style = PythonCommentStyle

    shebang = ""

    if style.SHEBANGS:
        for shebang_prefix in style.SHEBANGS:
            if text.startswith(shebang_prefix):
                shebang, text = _extract_shebang(shebang_prefix, text)
                break

    header = create_header(
        reuse_info,
        None,
        template=template,
        template_is_commented=template_is_commented,
        style=style,
        force_multi=force_multi,
        merge_copyrights=merge_copyrights,
    )

    new_text = f"{header}\n"
    if shebang.strip():
        new_text = f"{shebang.rstrip()}\n\n{new_text}"
    if text.strip():
        new_text = f"{new_text}\n{text.lstrip()}"
    return new_text
