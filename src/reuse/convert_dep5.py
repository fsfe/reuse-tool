# SPDX-FileCopyrightText: 2024 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Logic to convert a .reuse/dep5 file to a REUSE.toml file."""

import re
import sys
from argparse import ArgumentParser, Namespace
from gettext import gettext as _
from typing import IO, Any, Dict, Iterable, List, Optional, TypeVar, Union, cast

import tomlkit
from debian.copyright import Copyright, FilesParagraph, Header

from .global_licensing import REUSE_TOML_VERSION, ReuseDep5
from .project import Project

_SINGLE_ASTERISK_PATTERN = re.compile(r"(?<!\*)\*(?!\*)")

_T = TypeVar("_T")


def _collapse_list_if_one_item(
    # Technically this should be Sequence[_T], but I can't get that to work.
    sequence: List[_T],
) -> Union[List[_T], _T]:
    """Return the only item of the list if the length of the list is one, else
    return the list.
    """
    if len(sequence) == 1:
        return sequence[0]
    return sequence


def _header_from_dep5_header(
    header: Header,
) -> Dict[str, Union[str, List[str]]]:
    result: Dict[str, Union[str, List[str]]] = {}
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
) -> Union[str, List[str]]:
    return _collapse_list_if_one_item(
        [line.strip() for line in cast(str, paragraph.copyright).splitlines()]
    )


def _convert_asterisk(path: str) -> str:
    """This solves a semantics difference. A singular asterisk is semantically
    identical to a double asterisk in REUSE.toml.
    """
    return _SINGLE_ASTERISK_PATTERN.sub("**", path)


def _paths_from_paragraph(paragraph: FilesParagraph) -> Union[str, List[str]]:
    return _collapse_list_if_one_item(
        [_convert_asterisk(path) for path in list(paragraph.files)]
    )


def _comment_from_paragraph(paragraph: FilesParagraph) -> Optional[str]:
    return cast(Optional[str], paragraph.comment)


def _annotations_from_paragraphs(
    paragraphs: Iterable[FilesParagraph],
) -> List[Dict[str, Union[str, List[str]]]]:
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
    result: Dict[str, Any] = {"version": REUSE_TOML_VERSION}
    result.update(header)
    result["annotations"] = annotations
    return tomlkit.dumps(result)


# pylint: disable=unused-argument
def add_arguments(parser: ArgumentParser) -> None:
    """Add arguments to parser."""
    # Nothing to do.


# pylint: disable=unused-argument
def run(args: Namespace, project: Project, out: IO[str] = sys.stdout) -> int:
    """Convert .reuse/dep5 to REUSE.toml."""
    if not (project.root / ".reuse/dep5").exists():
        args.parser.error(_("no '.reuse/dep5' file"))

    text = toml_from_dep5(
        cast(ReuseDep5, project.global_licensing).dep5_copyright
    )
    (project.root / "REUSE.toml").write_text(text)
    (project.root / ".reuse/dep5").unlink()

    return 0
