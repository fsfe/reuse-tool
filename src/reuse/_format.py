# SPDX-FileCopyrightText: 2018 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Formatting functions primarily for the CLI."""

from textwrap import fill, indent

WIDTH = 78
INDENT = 2


def fill_paragraph(text, width=WIDTH, indent_width=0):
    """Wrap a single paragraph."""
    return indent(
        fill(text.strip(), width=width - indent_width), indent_width * " "
    )


def fill_all(text, width=WIDTH, indent_width=0):
    """Wrap all paragraphs."""
    return "\n\n".join(
        fill_paragraph(paragraph, width=width, indent_width=indent_width)
        for paragraph in split_into_paragraphs(text)
    )


def split_into_paragraphs(text):
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
