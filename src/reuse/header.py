# SPDX-Copyright: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Functions for manipulating the comment headers of files."""

import sys
from gettext import gettext as _

from boolean.boolean import ParseError
from license_expression import ExpressionError

from . import SpdxInfo
from ._comment import (
    COMMENT_STYLE_MAP,
    NAME_STYLE_MAP,
    CommentCreateError,
    CommentParseError,
    CommentStyle,
    PythonCommentStyle,
)
from ._util import _LICENSING, PathType, extract_spdx_info, make_copyright_line


# TODO: Add a template here maybe.
def _create_new_header(
    spdx_info: SpdxInfo, style: CommentStyle = PythonCommentStyle
) -> str:
    """Format a new header from scratch.

    :raises CommentCreateError: if a comment could not be created.
    """
    result = "\n\n".join(
        (
            "\n".join(sorted(spdx_info.copyright_lines)),
            "\n".join(
                (
                    "SPDX" "-License-Identifier: " + expr
                    for expr in sorted(map(str, spdx_info.spdx_expressions))
                )
            ),
        )
    )
    return style.create_comment(result)


# TODO: Add a template here maybe.
def create_header(
    spdx_info: SpdxInfo,
    header: str = None,
    style: CommentStyle = PythonCommentStyle,
) -> str:
    """Create a header containing *spdx_info*. *header* is an optional argument
    containing a header which should be modified to include *spdx_info*. If
    *header* is not given, a brand new header is created.

    :raises CommentCreateError: if a comment could not be created.
    """
    if header:
        try:
            existing_spdx = extract_spdx_info(header)
        except (ExpressionError, ParseError) as err:
            raise CommentCreateError(
                "existing header contains an erroneous SPDX expression"
            ) from err

        # FIXME: This behaviour does not match the docstring.
        spdx_info = SpdxInfo(
            spdx_info.spdx_expressions.union(existing_spdx.spdx_expressions),
            spdx_info.copyright_lines.union(existing_spdx.copyright_lines),
        )

    return _create_new_header(spdx_info, style=style)


def find_and_replace_header(
    text: str, spdx_info: SpdxInfo, style: CommentStyle = PythonCommentStyle
) -> str:
    """Find the comment block starting at the first character in *text*. That
    comment block is replaced by a new comment block containing *spdx_info*.

    If the comment block already contained some SPDX information, that
    information is merged into *spdx_info*.

    If no header exists, one is simply created.

    *text* is returned with a new header.

    :raises CommentCreateError: TODO FIXME
    """
    try:
        header = style.comment_at_first_character(text)
    except CommentParseError:
        # TODO: Log this
        header = None

    new_header = create_header(spdx_info, header, style=style)

    if header:
        text = text.replace(header + "\n", "", 1)
    else:
        # Some extra spacing for the new header.
        new_header = new_header + "\n"

    return new_header + "\n" + text


def add_arguments(parser) -> None:
    """Add arguments to parser."""
    parser.add_argument(
        "--copyright",
        "-c",
        action="append",
        type=str,
        help=_("copyright statement"),
    )
    parser.add_argument(
        "--license", "-l", action="append", type=str, help=_("SPDX Identifier")
    )
    parser.add_argument(
        "--style",
        action="store",
        type=str,
        choices=list(NAME_STYLE_MAP),
        help=_("comment style to use"),
    )
    parser.add_argument("path", action="store", nargs="+", type=PathType("w"))


def run(args, out=sys.stdout) -> int:
    """Add headers to files."""
    # TODO
    if not args.copyright:
        raise NotImplementedError()
    # TODO
    if not args.license:
        raise NotImplementedError()

    spdx_info = SpdxInfo(
        set(_LICENSING.parse(expr) for expr in args.license),
        set(make_copyright_line(x) for x in args.copyright),
    )

    for path in args.path:
        if args.style is not None:
            style = NAME_STYLE_MAP[args.style]
        else:
            try:
                style = COMMENT_STYLE_MAP[path.suffix]
            except KeyError:
                # FIXME: Throw an error instead!
                style = PythonCommentStyle

        with path.open("r") as fp:
            text = fp.read()

        output = find_and_replace_header(text, spdx_info, style=style)

        out.write(_("TODO"))

        with path.open("w") as fp:
            fp.write(output)

    return 0
