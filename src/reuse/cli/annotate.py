# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2019 Kirill Elagin <kirelagin@gmail.com>
# SPDX-FileCopyrightText: 2019 Stefan Bakker <s.bakker777@gmail.com>
# SPDX-FileCopyrightText: 2020 Dmitry Bogatov
# SPDX-FileCopyrightText: 2021 Alliander N.V. <https://alliander.com>
# SPDX-FileCopyrightText: 2021 Alvar Penning
# SPDX-FileCopyrightText: 2021 Robin Vobruba <hoijui.quaero@gmail.com>
# SPDX-FileCopyrightText: 2022 Carmen Bianca Bakker <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2022 Yaman Qalieh
# SPDX-FileCopyrightText: 2024 Rivos Inc.
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Click code for annotate subcommand."""

import datetime
import logging
import os
import sys
from collections.abc import Collection, Iterable, Sequence
from pathlib import Path
from typing import Any, cast

import click
from jinja2 import Environment, FileSystemLoader, Template
from jinja2.exceptions import TemplateNotFound

from .._annotate import add_header_to_file
from .._util import _determine_license_path, _determine_license_suffix_path
from ..comment import (
    NAME_STYLE_MAP,
    CommentStyle,
    get_comment_style,
    has_style,
    is_uncommentable,
)
from ..copyright import (
    CopyrightNotice,
    CopyrightPrefix,
    ReuseInfo,
    SpdxExpression,
    YearRange,
    validate_four_digits,
)
from ..exceptions import YearRangeParseError
from ..extract import HEURISTICS_CHUNK_SIZE, detect_encoding, detect_newline
from ..i18n import _
from ..project import Project
from .common import ClickObj, MutexOption, spdx_identifier
from .main import main

_LOGGER = logging.getLogger(__name__)


def test_mandatory_option_required(
    copyright_: Any,
    license_: Any,
    contributor: Any,
) -> None:
    """Raise a parser error if one of the mandatory options is not provided."""
    if not any((copyright_, license_, contributor)):
        raise click.UsageError(
            _(
                "Option '--copyright', '--license', or '--contributor' is"
                " required."
            )
        )


def all_paths(
    paths: Collection[Path],
    recursive: bool,
    project: Project,
) -> list[Path]:
    """Return a set of all provided paths, converted into .license paths if they
    exist. If *recursive* is enabled, all files belonging to *project* that are
    recursive children of *paths* are also added.

    Directories are filtered out.
    """
    if recursive:
        result: set[Path] = set()
        all_files = [path.resolve() for path in project.all_files()]
        for path in paths:
            if path.is_file():
                result.add(path)
            else:
                result |= {
                    child
                    for child in all_files
                    if path.resolve() in child.parents
                }
    else:
        result = set(paths)
    return [_determine_license_path(path) for path in result if path.is_file()]


def verify_paths_comment_style(
    style: Any,
    fallback_dot_license: Any,
    skip_unrecognised: Any,
    force_dot_license: Any,
    paths: Iterable[Path],
) -> None:
    """Exit if --style, --force-dot-license, --fallback-dot-license,
    or --skip-unrecognised is not enabled and one of the paths has an
    unrecognised style.
    """
    if (
        not style
        and not fallback_dot_license
        and not skip_unrecognised
        and not force_dot_license
    ):
        unrecognised_files: set[Path] = set()

        for path in paths:
            if not has_style(path):
                unrecognised_files.add(path)

        if unrecognised_files:
            raise click.UsageError(
                "{}\n\n{}".format(
                    _(
                        "The following files do not have a recognised file"
                        " extension. Please use '--style',"
                        " '--force-dot-license', '--fallback-dot-license', or"
                        " '--skip-unrecognised':"
                    ),
                    "\n".join(str(path) for path in unrecognised_files),
                )
            )


def verify_paths_line_handling(
    single_line: bool,
    multi_line: bool,
    forced_style: str | None,
    paths: Iterable[Path],
) -> None:
    """This function aborts the parser when --single-line or --multi-line is
    used, but the file type does not support that type of comment style.
    """
    for path in paths:
        style: type[CommentStyle] | None = None
        if forced_style is not None:
            style = NAME_STYLE_MAP.get(forced_style)
        if style is None:
            style = get_comment_style(path)
        # This shouldn't happen because of prior tests, so let's not bother with
        # this case.
        if style is None:
            continue
        # TODO: list all non-functional paths
        if single_line and not style.can_handle_single():
            raise click.UsageError(
                _(
                    "'{path}' does not support single-line comments, please"
                    " do not use '--single-line'."
                ).format(path=path.as_posix())
            )
        if multi_line and not style.can_handle_multi():
            raise click.UsageError(
                _(
                    "'{path}' does not support multi-line comments, please"
                    " do not use '--multi-line'."
                ).format(path=path.as_posix())
            )


def find_template(project: Project, name: str) -> Template:
    """Find a template given a name.

    Raises:
        TemplateNotFound: if template could not be found.
    """
    template_dir = project.root / ".reuse/templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)), trim_blocks=True
    )

    names = [name]
    if not name.endswith(".jinja2"):
        names.append(f"{name}.jinja2")
    if not name.endswith(".commented.jinja2"):
        names.append(f"{name}.commented.jinja2")

    for item in names:
        try:
            return env.get_template(item)
        except TemplateNotFound:
            pass
    raise TemplateNotFound(name)


def get_template(
    template_str: str | None, project: Project
) -> tuple[Template | None, bool]:
    """If a template is specified on the CLI, find and return it, including
    whether it is a 'commented' template.

    If no template is specified, just return None.
    """
    template: Template | None = None
    commented = False
    if template_str:
        try:
            template = cast(Template, find_template(project, template_str))
        except TemplateNotFound as error:
            raise click.UsageError(
                _("Template '{template}' could not be found.").format(
                    template=template_str
                )
            ) from error

        if ".commented" in Path(cast(str, template.name)).suffixes:
            commented = True
    return template, commented


def get_years(year: str | None, exclude_year: bool) -> tuple[YearRange, ...]:
    """Get the year. Normally it is today's year. If --year is specified,
    get a full tuple of ranges from that one.

    If --exclude-year is specified, return an empty tuple.
    """
    result: tuple[YearRange, ...] = tuple()
    if not exclude_year:
        if year:
            try:
                result = YearRange.tuple_from_string(year)
            except YearRangeParseError as error:
                raise click.UsageError(
                    _("'{year}' is not a valid year range.").format(year=year)
                ) from error
        else:
            try:
                current_year = str(datetime.date.today().year)
                result = (YearRange(validate_four_digits(current_year)),)
            except ValueError as error:
                raise click.UsageError(
                    _(
                        "Your operating system's year is set to '{year}'. This"
                        " is not four digits, and not supported."
                    ).format(year=current_year)
                ) from error
    return result


def get_reuse_info(
    copyrights: Collection[str],
    licenses: Collection[SpdxExpression],
    contributors: Collection[str],
    copyright_prefix: str | None,
    years: tuple[YearRange, ...],
) -> ReuseInfo:
    """Create a ReuseInfo object from --license, --copyright, and
    --contributor.
    """
    prefix = (
        CopyrightPrefix[CopyrightPrefix.uppercase_name(copyright_prefix)]
        if copyright_prefix is not None
        else CopyrightPrefix.SPDX
    )
    copyright_notices = {
        CopyrightNotice(item, years=years, prefix=prefix) for item in copyrights
    }

    return ReuseInfo(
        spdx_expressions=set(licenses),
        copyright_notices=copyright_notices,
        contributor_lines=set(contributors),
    )


_YEAR_MUTEX = ["years", "exclude_year"]
_LINE_MUTEX = ["single_line", "multi_line"]
_STYLE_MUTEX = [
    "force_dot_license",
    "fallback_dot_license",
    "skip_unrecognised",
]

_HELP = (
    _("Add copyright and licensing into the headers of files.")
    + "\n\n"
    + _(
        "By using --copyright and --license, you can specify which"
        " copyright holders and licenses to add to the headers of the"
        " given files."
    )
    + "\n\n"
    + _(
        "By using --contributor, you can specify people or entity that"
        " contributed but are not copyright holder of the given"
        " files."
    )
)


@main.command(name="annotate", help=_HELP)
@click.option(
    "--copyright",
    "-c",
    "copyrights",
    # TRANSLATORS: You may translate this. Please preserve capital letters.
    metavar=_("COPYRIGHT"),
    type=str,
    multiple=True,
    help=_("Copyright holder, repeatable."),
)
@click.option(
    "--license",
    "-l",
    "licenses",
    # TRANSLATORS: You may translate this. Please preserve capital letters.
    metavar=_("SPDX_IDENTIFIER"),
    type=spdx_identifier,
    multiple=True,
    help=_("SPDX License Identifier, repeatable."),
)
@click.option(
    "--contributor",
    "contributors",
    # TRANSLATORS: You may translate this. Please preserve capital letters.
    metavar=_("CONTRIBUTOR"),
    type=str,
    multiple=True,
    help=_("File contributor, repeatable."),
)
@click.option(
    "--year",
    "-y",
    "years",
    # TRANSLATORS: You may translate this. Please preserve capital letters.
    metavar=_("YEAR"),
    cls=MutexOption,
    mutually_exclusive=_YEAR_MUTEX,
    type=str,
    help=_(
        "Year of copyright notice. You may define multiple years or a range"
        " of years."
    ),
)
@click.option(
    "--style",
    "-s",
    cls=MutexOption,
    mutually_exclusive=["skip_unrecognised"],
    type=click.Choice(list(NAME_STYLE_MAP)),
    help=_("Comment style to use."),
)
@click.option(
    "--copyright-prefix",
    type=click.Choice(
        [
            CopyrightPrefix.lowercase_name(prefix.name)
            for prefix in CopyrightPrefix
        ]
    ),
    help=_("Copyright prefix to use."),
)
@click.option(
    "--copyright-style",
    "copyright_prefix",
    hidden=True,
)
@click.option(
    "--template",
    "-t",
    "template_str",
    # TRANSLATORS: You may translate this. Please preserve capital letters.
    metavar=_("TEMPLATE"),
    type=str,
    help=_("Name of template to use."),
)
@click.option(
    "--exclude-year",
    cls=MutexOption,
    mutually_exclusive=_YEAR_MUTEX,
    is_flag=True,
    help=_("Do not include year in copyright notice."),
)
@click.option(
    "--merge-copyrights",
    is_flag=True,
    help=_(
        "Merge copyright notices if they are identical except for their years."
    ),
)
@click.option(
    "--single-line",
    cls=MutexOption,
    mutually_exclusive=_LINE_MUTEX,
    is_flag=True,
    help=_("Force single-line comment style."),
)
@click.option(
    "--multi-line",
    cls=MutexOption,
    mutually_exclusive=_LINE_MUTEX,
    is_flag=True,
    help=_("Force multi-line comment style."),
)
@click.option(
    "--recursive",
    "-r",
    is_flag=True,
    help=_("Add headers to all files under specified directories recursively."),
)
@click.option(
    "--no-replace",
    is_flag=True,
    help=_("Do not replace the first header in the file; just add a new one."),
)
@click.option(
    "--force-dot-license",
    cls=MutexOption,
    mutually_exclusive=_STYLE_MUTEX,
    is_flag=True,
    help=_("Always write a .license file instead of a header inside the file."),
)
@click.option(
    "--fallback-dot-license",
    cls=MutexOption,
    mutually_exclusive=_STYLE_MUTEX,
    is_flag=True,
    help=_("Write a .license file to files with unrecognised comment styles."),
)
@click.option(
    "--skip-unrecognised",
    cls=MutexOption,
    mutually_exclusive=_STYLE_MUTEX,
    is_flag=True,
    help=_("Skip files with unrecognised comment styles."),
)
@click.option(
    "--skip-unrecognized",
    "skip_unrecognised",
    is_flag=True,
    hidden=True,
)
@click.option(
    "--skip-existing",
    is_flag=True,
    help=_("Skip files that already contain REUSE information."),
)
@click.argument(
    "paths",
    # TRANSLATORS: You may translate this. Please preserve capital letters.
    metavar=_("PATH"),
    type=click.Path(exists=True, writable=True, path_type=Path),
    nargs=-1,
)
@click.pass_obj
def annotate(
    obj: ClickObj,
    copyrights: Sequence[str],
    licenses: Sequence[SpdxExpression],
    contributors: Sequence[str],
    years: str | None,
    style: str | None,
    copyright_prefix: str | None,
    template_str: str | None,
    exclude_year: bool,
    merge_copyrights: bool,
    single_line: bool,
    multi_line: bool,
    recursive: bool,
    no_replace: bool,
    force_dot_license: bool,
    fallback_dot_license: bool,
    skip_unrecognised: bool,
    skip_existing: bool,
    paths: Sequence[Path],
) -> None:
    # pylint: disable=too-many-arguments,too-many-locals,missing-function-docstring
    project = obj.project

    test_mandatory_option_required(copyrights, licenses, contributors)
    paths = all_paths(paths, recursive, project)
    verify_paths_comment_style(
        style, fallback_dot_license, skip_unrecognised, force_dot_license, paths
    )
    # Verify line handling and comment styles before proceeding.
    verify_paths_line_handling(single_line, multi_line, style, paths)
    template, commented = get_template(template_str, project)
    years_tuple = get_years(years, exclude_year)
    reuse_info = get_reuse_info(
        copyrights, licenses, contributors, copyright_prefix, years_tuple
    )

    result = 0
    for path in paths:
        with path.open("rb") as fp:
            chunk = fp.read(HEURISTICS_CHUNK_SIZE)
        encoding = detect_encoding(chunk)
        newline = (
            detect_newline(chunk, encoding=encoding)
            if encoding is not None
            else os.linesep
        )
        if encoding is None or is_uncommentable(path) or force_dot_license:
            new_path = _determine_license_suffix_path(path)
            if encoding is None:
                _LOGGER.info(
                    _(
                        "'{path}' is a binary, therefore using '{new_path}'"
                        " for the header"
                    ).format(path=path, new_path=new_path)
                )
                encoding = "utf_8"
            path = Path(new_path)
            path.touch()
        result += add_header_to_file(
            path=path,
            reuse_info=reuse_info,
            template=template,
            template_is_commented=commented,
            style=style,
            encoding=encoding,
            newline=newline,
            force_multi=multi_line,
            skip_existing=skip_existing,
            skip_unrecognised=skip_unrecognised,
            fallback_dot_license=fallback_dot_license,
            merge_copyrights=merge_copyrights,
            replace=not no_replace,
            out=sys.stdout,
        )

    sys.exit(min(result, 1))
