# SPDX-FileCopyrightText: 2018 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Formatting functions primarily for the CLI."""

from textwrap import fill, indent
from typing import Iterator

WIDTH = 78
INDENT = 2


def fill_paragraph(text: str, width: int = WIDTH, indent_width: int = 0) -> str:
    """Wrap a single paragraph."""
    return indent(
        fill(text.strip(), width=width - indent_width), indent_width * " "
    )


def fill_all(text: str, width: int = WIDTH, indent_width: int = 0) -> str:
    """Wrap all paragraphs."""
    return "\n\n".join(
        fill_paragraph(paragraph, width=width, indent_width=indent_width)
        for paragraph in split_into_paragraphs(text)
    )


def split_into_paragraphs(text: str) -> Iterator[str]:
    """Yield all paragraphs in a text. A paragraph is a piece of text
    surrounded by empty lines.
    """
    lines = text.splitlines()
    paragraph = ""

    for line in lines:
        if not line:
            if paragraph:
                yield paragraph
                paragraph = ""
            else:
                continue
        else:
            if paragraph:
                padding = " "
            else:
                padding = ""
            paragraph = f"{paragraph}{padding}{line}"
    if paragraph:
        yield paragraph
