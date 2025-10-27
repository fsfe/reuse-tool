# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2024 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
# SPDX-FileCopyrightText: 2024 Kerry McAdams <github@klmcadams>
# SPDX-FileCopyrightText: 2024 Emil Velikov <emil.l.velikov@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Entry function for reuse."""

import gettext
import logging
import os
import warnings
from pathlib import Path

import click
from click.formatting import wrap_text

from .. import __REUSE_version__
from .._util import setup_logging
from ..i18n import _
from .common import ClickObj

_PACKAGE_PATH = os.path.dirname(os.path.dirname(__file__))
_LOCALE_DIR = os.path.join(_PACKAGE_PATH, "locale")
if gettext.find("reuse", localedir=_LOCALE_DIR):
    gettext.bindtextdomain("reuse", _LOCALE_DIR)
    # This is needed to make Click recognise our translations. Our own
    # translations use the class-based API.
    gettext.textdomain("reuse")


_VERSION_TEXT = (
    _("%(prog)s, version %(version)s")
    + "\n\n"
    + _(
        "This program is free software: you can redistribute it and/or modify"
        " it under the terms of the GNU General Public License as published by"
        " the Free Software Foundation, either version 3 of the License, or"
        " (at your option) any later version."
    )
    + "\n\n"
    + _(
        "This program is distributed in the hope that it will be useful,"
        " but WITHOUT ANY WARRANTY; without even the implied warranty of"
        " MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the"
        " GNU General Public License for more details."
    )
    + "\n\n"
    + _(
        "You should have received a copy of the GNU General Public License"
        " along with this program. If not, see"
        " <https://www.gnu.org/licenses/>."
    )
)

_HELP = (
    _(
        "reuse is a tool for compliance with the REUSE"
        " recommendations. See <https://reuse.software/> for more"
        " information, and <https://reuse.readthedocs.io/> for the online"
        " documentation."
    )
    + "\n\n"
    + _(
        "This version of reuse is compatible with version {} of the REUSE"
        " Specification."
    ).format(__REUSE_version__)
    + "\n\n"
    + _("Support the FSFE's work:")
    + "\n\n"
    # Indent next paragraph.
    + "   "
    + _(
        "Donations are critical to our strength and autonomy. They enable us"
        " to continue working for Free Software wherever necessary. Please"
        " consider making a donation at <https://fsfe.org/donate/>."
    )
)


@click.group(name="reuse", help=_HELP)
@click.option(
    "--debug",
    is_flag=True,
    help=_("Enable debug statements."),
)
@click.option(
    "--suppress-deprecation",
    is_flag=True,
    help=_("Hide deprecation warnings."),
)
@click.option(
    "--include-submodules",
    is_flag=True,
    help=_("Do not skip over Git submodules."),
)
@click.option(
    "--include-meson-subprojects",
    is_flag=True,
    help=_("Do not skip over Meson subprojects."),
)
@click.option(
    "--no-multiprocessing",
    is_flag=True,
    help=_("Do not use multiprocessing."),
)
@click.option(
    "--root",
    type=click.Path(
        exists=True,
        file_okay=False,
        path_type=Path,
    ),
    default=None,
    help=_("Define root of project."),
)
@click.version_option(
    package_name="reuse",
    message=wrap_text(_VERSION_TEXT, preserve_paragraphs=True),
)
@click.pass_context
def main(
    ctx: click.Context,
    debug: bool,
    suppress_deprecation: bool,
    include_submodules: bool,
    include_meson_subprojects: bool,
    no_multiprocessing: bool,
    root: Path | None,
) -> None:
    # pylint: disable=missing-function-docstring,too-many-arguments
    setup_logging(level=logging.DEBUG if debug else logging.WARNING)

    # Very stupid workaround to not print a DEP5 deprecation warning in the
    # middle of ccompileonversion to REUSE.toml.
    if ctx.invoked_subcommand == "convert-dep5":
        os.environ["_SUPPRESS_DEP5_WARNING"] = "1"

    if not suppress_deprecation:
        warnings.filterwarnings("default", module="reuse")

    ctx.obj = ClickObj(
        root=root,
        include_submodules=include_submodules,
        include_meson_subprojects=include_meson_subprojects,
        no_multiprocessing=no_multiprocessing,
    )
