# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2023 Nico Rikken <nico.rikken@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Click code for download subcommand."""

import logging
import sys
from collections.abc import Collection
from difflib import SequenceMatcher
from pathlib import Path
from typing import IO
from urllib.error import URLError

import click

from .._licenses import ALL_MAP, ALL_NON_DEPRECATED_MAP
from .._util import _strip_plus_from_identifier
from ..download import _path_to_license_file, put_license_in_file
from ..i18n import _
from ..report import ProjectReport
from ..types import StrPath
from .common import ClickObj, MutexOption
from .main import main

_LOGGER = logging.getLogger(__name__)


def _similar_spdx_identifiers(identifier: str) -> list[str]:
    """Given an incorrect SPDX identifier, return a list of similar ones."""
    suggestions: list[str] = []
    for valid_identifier in ALL_NON_DEPRECATED_MAP:
        distance = SequenceMatcher(
            a=identifier.lower(), b=valid_identifier[: len(identifier)].lower()
        ).ratio()
        if distance > 0.75:
            suggestions.append(valid_identifier)
    suggestions = sorted(suggestions)

    return suggestions


def _print_incorrect_spdx_identifier(
    identifier: str, out: IO[str] = sys.stdout
) -> None:
    """Print out that *identifier* is not valid, and follow up with some
    suggestions.
    """
    out.write(
        _("'{}' is not a valid SPDX License Identifier.").format(identifier)
    )
    out.write("\n")

    suggestions = _similar_spdx_identifiers(identifier)
    if suggestions:
        out.write("\n")
        out.write(_("Did you mean:"))
        out.write("\n")
        for suggestion in suggestions:
            out.write(f"* {suggestion}\n")
        out.write("\n")
    out.write(
        _(
            "See <https://spdx.org/licenses/> for a list of valid "
            "SPDX License Identifiers."
        )
    )
    out.write("\n")


def _already_exists(path: StrPath) -> None:
    click.echo(
        _("Error: {spdx_identifier} already exists.").format(
            spdx_identifier=path
        )
    )


def _not_found(path: StrPath) -> None:
    click.echo(_("Error: {path} does not exist.").format(path=path))


def _could_not_download(identifier: str) -> None:
    click.echo(_("Error: Failed to download license."))
    click.echo("")
    if identifier not in ALL_MAP:
        _print_incorrect_spdx_identifier(identifier, out=sys.stdout)
    else:
        click.echo(_("Is your internet connection working?"))


def _successfully_downloaded(destination: StrPath) -> None:
    click.echo(
        _("Successfully downloaded {spdx_identifier}.").format(
            spdx_identifier=destination
        )
    )


_ALL_MUTEX = ["all_", "output"]


_HELP = (
    _("Download a license and place it in the LICENSES/ directory.")
    + "\n\n"
    + _(
        "LICENSE must be a valid SPDX License Identifier. You may specify"
        " LICENSE multiple times to download multiple licenses."
    )
)


@main.command(name="download", help=_HELP)
@click.option(
    "--all",
    "all_",
    cls=MutexOption,
    mutually_exclusive=_ALL_MUTEX,
    is_flag=True,
    help=_("Download all missing licenses detected in the project."),
)
@click.option(
    "--output",
    "-o",
    cls=MutexOption,
    mutually_exclusive=_ALL_MUTEX,
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help=_("Path to download to."),
)
@click.option(
    "--source",
    type=click.Path(exists=True, readable=True, path_type=Path),
    help=_(
        "Source from which to copy custom LicenseRef- licenses, either"
        " a directory that contains the file or the file itself."
    ),
)
@click.argument(
    "licenses",
    # TRANSLATORS: You may translate this. Please preserve capital letters.
    metavar=_("LICENSE"),
    type=str,
    nargs=-1,
)
@click.pass_obj
def download(
    obj: ClickObj,
    licenses: Collection[str],
    all_: bool,
    output: Path | None,
    source: Path | None,
) -> None:
    # pylint: disable=missing-function-docstring
    if all_ and licenses:
        raise click.UsageError(
            _(
                "The 'LICENSE' argument and '--all' option are mutually"
                " exclusive."
            )
        )

    if all_:
        # TODO: This is fairly inefficient, but gets the job done.
        report = ProjectReport.generate(obj.project, do_checksum=False)
        licenses = report.missing_licenses.keys()

    if len(licenses) > 1 and output:
        raise click.UsageError(
            _("Cannot use '--output' with more than one license.")
        )

    licenses = {_strip_plus_from_identifier(lic) for lic in licenses}
    return_code = 0
    for lic in licenses:
        destination: Path = output  # type: ignore
        if destination is None:
            destination = _path_to_license_file(lic, obj.project)
        try:
            put_license_in_file(lic, destination=destination, source=source)
        except URLError:
            _could_not_download(lic)
            return_code = 1
        except FileExistsError as err:
            _already_exists(err.filename)
            return_code = 1
        except FileNotFoundError as err:
            _not_found(err.filename)
            return_code = 1
        else:
            _successfully_downloaded(destination)
    sys.exit(return_code)
