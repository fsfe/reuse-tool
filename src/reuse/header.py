# SPDX-Copyright: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Functions for manipulating the comment headers of files."""

import argparse
import sys
from gettext import gettext as _
from pathlib import Path

from . import SpdxInfo
from ._comment import CommentStyle, PythonCommentStyle
from ._util import _LICENSING


# TODO: Add a template here maybe.
def _create_new_header(
    spdx_info: SpdxInfo, style: CommentStyle = PythonCommentStyle
) -> str:
    """Format a new header from scratch.

    :raises CommentCreateError: if a comment could not be created.
    """
    result = "\n\n".join(
        (
            "\n".join(
                (
                    "SPDX" "-Copyright: " + line
                    for line in sorted(spdx_info.copyright_lines)
                )
            ),
            "\n".join(
                (
                    "SPDX" "-License-Identifier: " + str(expr)
                    for expr in sorted(spdx_info.spdx_expressions)
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
    if header is None:
        return _create_new_header(spdx_info, style=style)
    raise NotImplementedError()


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
        "path", action="store", nargs="+", type=argparse.FileType("r")
    )


def run(args, out=sys.stdout) -> int:
    """Add headers to files."""
    if not args.copyright:
        raise NotImplementedError()
    if not args.license:
        raise NotImplementedError()

    spdx_info = SpdxInfo(
        set(_LICENSING.parse(expr) for expr in args.license),
        set(args.copyright),
    )

    for path in args.path:
        # We won't be using this stream.
        path.close()
        path = Path(path.buffer.name)

        with path.open("r") as fp:
            text = fp.read()

        # TODO: Extract to separate function, probably.
        # TODO: Read the current header.
        # TODO: Detect file type
        # Basically, this is utterly broken, but works for the most basic case,
        # which is great during early testing.
        output = create_header(spdx_info) + "\n\n" + text
        out.write(_("TODO"))

        with path.open("w") as fp:
            fp.write(output)

    return 0
