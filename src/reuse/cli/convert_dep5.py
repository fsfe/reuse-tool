# SPDX-FileCopyrightText: 2024 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: 2024 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Click code for convert-dep5 subcommand."""

from typing import cast

import click

from ..convert_dep5 import toml_from_dep5
from ..global_licensing import ReuseDep5
from ..i18n import _
from .common import ClickObj
from .main import main

_HELP = _(
    "Convert .reuse/dep5 into a REUSE.toml file. The generated file is placed"
    " in the project root and is semantically identical. The .reuse/dep5 file"
    " is subsequently deleted."
)


@main.command(name="convert-dep5", help=_HELP)
@click.pass_obj
def convert_dep5(obj: ClickObj) -> None:
    # pylint: disable=missing-function-docstring
    project = obj.project
    if not (project.root / ".reuse/dep5").exists():
        raise click.UsageError(_("No '.reuse/dep5' file."))

    text = toml_from_dep5(
        cast(ReuseDep5, project.global_licensing).dep5_copyright
    )
    (project.root / "REUSE.toml").write_text(text)
    (project.root / ".reuse/dep5").unlink()
