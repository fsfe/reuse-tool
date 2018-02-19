# -*- coding: utf-8 -*-
#
# Copyright (C) 2018  Carmen Bianca Bakker
#
# This file is part of reuse, available from its original location:
# <https://git.fsfe.org/reuse/reuse/>.
#
# reuse is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# reuse is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# reuse.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Formatting functions primarily for the CLI."""

from textwrap import indent, fill

WIDTH = 78
INDENT = 2


def fill_paragraph(text, width=WIDTH, indent_width=0):
    """Wrap a single paragraph."""
    return indent(
        fill(text.strip(), width=width - indent_width), indent_width * ' ')


def fill_all(text, width=WIDTH, indent_width=0):
    """Wrap all paragraphs."""
    return '\n\n'.join(
        fill_paragraph(paragraph, width=width, indent_width=indent_width)
        for paragraph in split_into_paragraphs(text))


def split_into_paragraphs(text):
    """Yield all paragraphs in a text.  A paragraph is a piece of text
    surrounded by empty lines.
    """
    lines = text.splitlines()
    paragraph = ''

    for line in lines:
        if not line:
            if paragraph:
                yield paragraph
                paragraph = ''
            else:
                continue
        else:
            if paragraph:
                padding = ' '
            else:
                padding = ''
            paragraph = '{}{}{}'.format(paragraph, padding, line)
    if paragraph:
        yield paragraph
