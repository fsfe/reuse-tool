# SPDX-Copyright: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Functions for manipulating the comment headers of files."""

from . import SpdxInfo
from ._comment import CommentStyle, PythonCommentStyle


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
