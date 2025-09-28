# SPDX-FileCopyrightText: 2024 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Logic to convert a .reuse/dep5 file to a REUSE.toml file."""

import re
from collections.abc import Iterable
from typing import Any, Optional, TypeVar, cast

import tomlkit
from debian.copyright import Copyright, FilesParagraph, Header

from .global_licensing import REUSE_TOML_VERSION

_SINGLE_ASTERISK_PATTERN = re.compile(r"(?<!\*)\*(?!\*)")

_T = TypeVar("_T")


def _collapse_list_if_one_item(
    # Technically this should be Sequence[_T], but I can't get that to work.
    sequence: list[_T],
) -> list[_T] | _T:
    """Return the only item of the list if the length of the list is one, else
    return the list.
    """
    if len(sequence) == 1:
        return sequence[0]
    return sequence


def _header_from_dep5_header(
    header: Header,
) -> dict[str, str | list[str]]:
    result: dict[str, str | list[str]] = {}
    if header.upstream_name:
        result["SPDX-PackageName"] = str(header.upstream_name)
    if header.upstream_contact:
        result["SPDX-PackageSupplier"] = _collapse_list_if_one_item(
            list(map(str, header.upstream_contact))
        )
    if header.source:
        result["SPDX-PackageDownloadLocation"] = str(header.source)
    if header.disclaimer:
        result["SPDX-PackageComment"] = str(header.disclaimer)
    return result


def _copyrights_from_paragraph(
    paragraph: FilesParagraph,
) -> str | list[str]:
    return _collapse_list_if_one_item(
        [line.strip() for line in cast(str, paragraph.copyright).splitlines()]
    )


def _convert_asterisk(path: str) -> str:
    """This solves a semantics difference. A singular asterisk is semantically
    identical to a double asterisk in REUSE.toml.
    """
    return _SINGLE_ASTERISK_PATTERN.sub("**", path)


def _paths_from_paragraph(paragraph: FilesParagraph) -> str | list[str]:
    return _collapse_list_if_one_item(
        [_convert_asterisk(path) for path in list(paragraph.files)]
    )


def _comment_from_paragraph(paragraph: FilesParagraph) -> str | None:
    return cast(Optional[str], paragraph.comment)


def _annotations_from_paragraphs(
    paragraphs: Iterable[FilesParagraph],
) -> list[dict[str, str | list[str]]]:
    annotations = []
    for paragraph in paragraphs:
        copyrights = _copyrights_from_paragraph(paragraph)
        paths = _paths_from_paragraph(paragraph)
        paragraph_result = {
            "path": paths,
            "precedence": "aggregate",
            "SPDX-FileCopyrightText": copyrights,
            "SPDX-License-Identifier": paragraph.license.to_str(),
        }
        comment = _comment_from_paragraph(paragraph)
        if comment:
            paragraph_result["SPDX-FileComment"] = comment
        annotations.append(paragraph_result)
    return annotations


def toml_from_dep5(dep5: Copyright) -> str:
    """Given a Copyright object, return an equivalent REUSE.toml string."""
    header = _header_from_dep5_header(dep5.header)
    annotations = _annotations_from_paragraphs(dep5.all_files_paragraphs())
    result: dict[str, Any] = {"version": REUSE_TOML_VERSION}
    result.update(header)
    result["annotations"] = annotations
    return tomlkit.dumps(result)
