# SPDX-FileCopyrightText: 2024 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Logic to convert a .reuse/dep5 file to a REUSE.toml file."""

import re
import sys
from argparse import ArgumentParser, Namespace
from gettext import gettext as _
from typing import IO, Any, List, Union, cast

import tomlkit
from debian.copyright import Copyright

from .global_licensing import REUSE_TOML_VERSION, ReuseDep5
from .project import Project

_SINGLE_ASTERISK_PATTERN = re.compile(r"(?<!\*)\*(?!\*)")


def _convert_asterisk(path: str) -> str:
    """This solves a semantics difference. A singular asterisk is semantically
    identical to a double asterisk in REUSE.toml.
    """
    return _SINGLE_ASTERISK_PATTERN.sub("**", path)


def toml_from_dep5(dep5: Copyright) -> str:
    """Given a Copyright object, return an equivalent REUSE.toml string."""
    annotations = []
    for paragraph in dep5.all_files_paragraphs():
        # Convert some lists to single-item elements as necessary.
        copyrights: Union[str, List[str]] = [
            line.strip() for line in cast(str, paragraph.copyright).splitlines()
        ]
        if len(copyrights) == 1:
            copyrights = copyrights[0]
        paths: Union[str, List[str]] = list(paragraph.files)
        paths = [_convert_asterisk(path) for path in paths]
        if len(paths) == 1:
            paths = paths[0]
        annotations.append(
            {
                "path": paths,
                "precedence": "aggregate",
                "SPDX-FileCopyrightText": copyrights,
                "SPDX-License-Identifier": cast(
                    Any, paragraph.license
                ).synopsis,
            }
        )
    return tomlkit.dumps(
        {"version": REUSE_TOML_VERSION, "annotations": annotations}
    )


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
