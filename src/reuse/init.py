# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Functions for REUSE-ifying a project."""

import sys
from gettext import gettext as _
from inspect import cleandoc
from pathlib import Path
from typing import List, Mapping, IO, Union

import requests
import toml

from ._licenses import ALL_NON_DEPRECATED_MAP
from ._util import PathType, print_incorrect_spdx_identifier
from .download import _path_to_license_file, put_license_in_file
from .project import Project
from .vcs import find_root


def prompt_licenses(out=sys.stdout) -> List[str]:
    """Prompt the user for a list of licenses."""
    first = _(
        "What license is your project under? "
        "Provide the SPDX License Identifier."
    )
    multi = _(
        "What other license is your project under? "
        "Provide the SPDX License Identifier."
    )
    licenses = []

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
        if result not in ALL_NON_DEPRECATED_MAP:
            print_incorrect_spdx_identifier(result, out=out)
            out.write("\n\n")
        else:
            licenses.append(result)


def add_arguments(parser):
    """Add arguments to parser."""
    parser.add_argument(
        "path",
        action="store",
        nargs="?",
        type=PathType("r", force_directory=True),
    )


def read_pyproject_toml(
    path: Path, out: IO
) -> Mapping[str, Union[str, List[str]]]:
    """Parse information from pyproject.toml"""
    out.write(_("Using information from pyproject.toml."))
    out.write("\n")
    doc = toml.load(path)
    project = doc.get("project")
    config = {}

    if "license" in project:
        license = project["license"].get("text")
        if license not in ALL_NON_DEPRECATED_MAP:
            print_incorrect_spdx_identifier(license, out)
            out.write("\n")
        else:
            config["licenses"] = [license]

    if "name" in project:
        config["project_name"] = project["name"]

    homepage = project.get("urls", {}).get("homepage")
    if homepage:
        config["project_url"] = homepage

    authors = project.get("authors", [])
    if authors:
        config["contact_name"] = authors[0]["name"]
        config["contact_address"] = authors[0]["email"]

    return config


def run(args, project: Project, out=sys.stdout):
    """List all non-compliant files."""
    # pylint: disable=too-many-statements,unused-argument
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

    if (root / "pyproject.toml").exists():
        config = read_pyproject_toml(root / "pyproject.toml", out)

    out.write(_("Initializing project for REUSE."))
    out.write("\n\n")

    licenses = config.get("licenses") or prompt_licenses(out=out)

    project_name = config.get("project_name")
    if not project_name:
        out.write(_("What is the name of the project?"))
        out.write("\n")
        project_name = config.get("project_name") or input()
        out.write("\n")

    project_url = config.get("project_url") or input()
    if not project_url:
        out.write(_("What is the internet address of the project?"))
        out.write("\n")
        project_url = input()
        out.write("\n")

    contact_name = config.get("contact_name")
    if not contact_name:
        out.write(_("What is the name of the maintainer?"))
        out.write("\n")
        contact_name = input()
        out.write("\n")

    contact_address = config.get("contact_address") or input()
    if not contact_address:
        out.write(_("What is the e-mail address of the maintainer?"))
        out.write("\n")
        contact_address = input()
        out.write("\n")

    out.write(_("All done! Initializing now."))
    out.write("\n\n")

    # Creating files past this point!

    for lic in licenses:
        destination = _path_to_license_file(lic, root=root)
        try:
            out.write(_("Downloading {}").format(lic))
            out.write("\n")
            put_license_in_file(lic, destination=destination)
        # TODO: exceptions
        except FileExistsError:
            out.write(_("{} already exists").format(destination))
            out.write("\n")
        except requests.RequestException:
            out.write(_("Could not download {}").format(lic))
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
