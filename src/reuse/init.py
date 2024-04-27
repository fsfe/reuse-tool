# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2024 Ngô Ngọc Đức Huy <huyngo@disroot.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Functions for REUSE-ifying a project."""

import os
import re
import sys
from argparse import ArgumentParser, Namespace
from gettext import gettext as _
from inspect import cleandoc
from pathlib import Path
from typing import IO, List
from urllib.error import URLError

from ._licenses import ALL_NON_DEPRECATED_MAP
from ._util import (
    _LICENSEREF_PATTERN,
    PathType,
    print_incorrect_spdx_identifier,
)
from .download import _path_to_license_file, put_license_in_file
from .project import Project
from .vcs import find_root


def prompt_licenses(out: IO[str] = sys.stdout) -> List[str]:
    """Prompt the user for a list of licenses."""
    first = _(
        "What license is your project under? "
        "Provide the SPDX License Identifier. "
        "See <https://spdx.org/licenses/> for the list."
    )
    multi = _(
        "What other license is your project under? "
        "Provide the SPDX License Identifier."
    )
    licenses: List[str] = []

    while True:
        if not licenses:
            out.write(first)
        else:
            out.write(multi)
        out.write("\n")
        out.write(_("To stop adding licenses, hit RETURN."))
        out.write("\n")
        result = input()
        out.write("\n")
        if not result:
            return licenses
        if result not in ALL_NON_DEPRECATED_MAP and not re.match(
            _LICENSEREF_PATTERN, result
        ):
            print_incorrect_spdx_identifier(result, out=out)
            out.write("\n\n")
        else:
            licenses.append(result)


def prompt(question: str, out: IO[str] = sys.stdout) -> str:
    """Prompt for value."""
    out.write(question)
    out.write("\n")
    value = input()
    out.write("\n")
    return value


def filter_invalid_licenses(licenses: List[str],
                            out: IO[str] = sys.stdout) -> List[str]:
    """Check if licenses in a list are valid, and prompt again if none is."""
    filtered_licenses = []
    for _license in licenses:
        if _license not in ALL_NON_DEPRECATED_MAP and not re.match(
            _LICENSEREF_PATTERN, _license
        ):
            print_incorrect_spdx_identifier(_license, out=out)
            out.write("\n\n")
        else:
            filtered_licenses.append(_license)
    if len(filtered_licenses) == 0:
        licenses = prompt_licenses(out=out)
    else:
        out.write(_("Chosen licenses:"))
        out.write("\n")
        for _license in licenses:
            out.write(_license)
            out.write("\n")
        out.write("\n")
    return filtered_licenses


def add_arguments(parser: ArgumentParser) -> None:
    """Add arguments to parser."""
    parser.add_argument(
        "path",
        action="store",
        nargs="?",
        type=PathType("r", force_directory=True),
    )
    parser.add_argument(
        "--licenses",
        action="store",
        nargs="*",
        type=str
    )
    parser.add_argument(
        "--project-name",
        type=str
    )
    parser.add_argument(
        "--project-address",
        type=str
    )
    parser.add_argument(
        "--maintainer",
        type=str
    )
    parser.add_argument(
        "--email",
        type=str
    )


def run(
    args: Namespace,
    project: Project,
    out: IO[str] = sys.stdout,
) -> int:
    """Initialize project."""
    # pylint: disable=unused-argument
    if args.path:
        root = args.path
    else:
        root = find_root()
    if root is None:
        root = Path.cwd()

    if (root / ".reuse").exists():
        out.write(_("Project already initialized"))
        out.write("\n")
        return 1

    out.write(_("Initializing project for REUSE."))
    out.write("\n\n")

    if args.licenses:
        licenses = filter_invalid_licenses(args.licenses, out)
    elif (env_licenses := os.getenv("REUSE_LICENSES")) is not None:
        licenses = filter_invalid_licenses(env_licenses.split(), out)
    else:
        licenses = prompt_licenses(out=out)

    project_name = (args.project_name or
                    prompt(_("What is the name of the project?"), out))

    project_url = (args.project_address or
                   prompt(
                       _("What is the internet address of the project?"), out))

    contact_name = (args.maintainer or
                    os.getenv("REUSE_MAINTAINER") or
                    prompt(_("What is the name of the maintainer?"), out))

    contact_address = (
        args.email or
        os.getenv("REUSE_EMAIL") or
        prompt(_("What is the e-mail address of the maintainer?"), out))

    out.write(_("All done! Initializing now."))
    out.write("\n\n")

    # Creating files past this point!

    for lic in licenses:
        destination = _path_to_license_file(lic, root=root)

        try:
            out.write(_("Retrieving {}").format(lic))
            out.write("\n")
            put_license_in_file(lic, destination=destination)
        # TODO: exceptions
        except FileExistsError:
            out.write(_("{} already exists").format(destination))
            out.write("\n")
        except URLError:
            out.write(_("Could not download {}").format(lic))
            out.write("\n")
        except FileNotFoundError as err:
            out.write(
                _(
                    "Error: Could not copy {path}, "
                    "please add {lic}.txt manually in the LICENCES/ directory."
                ).format(path=err.filename, lic=lic)
            )
            out.write("\n")

    out.write("\n")

    out.write(_("Creating .reuse/dep5"))
    out.write("\n\n")

    # pylint: disable=line-too-long
    dep5_text = cleandoc(
        f"""
        Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
        Upstream-Name: {project_name}
        Upstream-Contact: {contact_name} <{contact_address}>
        Source: {project_url}

        # Sample paragraph, commented out:
        #
        # Files: src/*
        # Copyright: $YEAR $NAME <$CONTACT>
        # License: ...
        """
    )
    dep5_text += "\n"

    (root / ".reuse").mkdir()
    (root / ".reuse/dep5").write_text(dep5_text)

    out.write(_("Initialization complete."))
    out.write("\n")

    return 0
