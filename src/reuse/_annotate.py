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

"""Functions for the CLI portion of manipulating headers."""

import datetime
import logging
import os
import sys
from argparse import SUPPRESS, ArgumentParser, Namespace
from gettext import gettext as _
from pathlib import Path
from typing import IO, Iterable, Optional, Set, Tuple, Type, cast

from binaryornot.check import is_binary
from jinja2 import Environment, FileSystemLoader, Template
from jinja2.exceptions import TemplateNotFound

from . import ReuseInfo
from ._util import (
    _COPYRIGHT_PREFIXES,
    PathType,
    StrPath,
    _determine_license_path,
    _determine_license_suffix_path,
    _get_comment_style,
    _has_style,
    _is_uncommentable,
    contains_reuse_info,
    detect_line_endings,
    make_copyright_line,
    spdx_identifier,
)
from .comment import (
    NAME_STYLE_MAP,
    CommentCreateError,
    CommentStyle,
    EmptyCommentStyle,
)
from .header import MissingReuseInfo, add_new_header, find_and_replace_header
from .project import Project

_LOGGER = logging.getLogger(__name__)


def verify_paths_line_handling(
    args: Namespace,
    paths: Iterable[Path],
) -> None:
    """This function aborts the parser when --single-line or --multi-line is
    used, but the file type does not support that type of comment style.
    """
    for path in paths:
        style = NAME_STYLE_MAP.get(args.style)
        if style is None:
            style = _get_comment_style(path)
        if style is None:
            continue
        if args.single_line and not style.can_handle_single():
            args.parser.error(
                _(
                    "'{path}' does not support single-line comments, please"
                    " do not use --single-line"
                ).format(path=path)
            )
        if args.multi_line and not style.can_handle_multi():
            args.parser.error(
                _(
                    "'{path}' does not support multi-line comments, please"
                    " do not use --multi-line"
                ).format(path=path)
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


def add_header_to_file(
    path: StrPath,
    reuse_info: ReuseInfo,
    template: Optional[Template],
    template_is_commented: bool,
    style: Optional[str],
    force_multi: bool = False,
    skip_existing: bool = False,
    skip_unrecognised: bool = False,
    fallback_dot_license: bool = False,
    merge_copyrights: bool = False,
    replace: bool = True,
    out: IO[str] = sys.stdout,
) -> int:
    """Helper function."""
    # pylint: disable=too-many-arguments,too-many-locals
    result = 0
    comment_style: Optional[Type[CommentStyle]] = NAME_STYLE_MAP.get(
        cast(str, style)
    )
    if comment_style is None:
        comment_style = _get_comment_style(path)
    if comment_style is None:
        if skip_unrecognised:
            out.write(_("Skipped unrecognised file '{path}'").format(path=path))
            out.write("\n")
            return result
        if fallback_dot_license:
            out.write(
                _(
                    "'{path}' is not recognised; creating '{path}.license'"
                ).format(path=path)
            )
            out.write("\n")
            path = _determine_license_suffix_path(path)
            path.touch()
            comment_style = EmptyCommentStyle

    with open(path, "r", encoding="utf-8", newline="") as fp:
        text = fp.read()

    # Ideally, this check is done elsewhere. But that would necessitate reading
    # the file contents before this function is called.
    if skip_existing and contains_reuse_info(text):
        out.write(
            _(
                "Skipped file '{path}' already containing REUSE information"
            ).format(path=path)
        )
        out.write("\n")
        return result

    # Detect and remember line endings for later conversion.
    line_ending = detect_line_endings(text)
    # Normalise line endings.
    text = text.replace(line_ending, "\n")

    try:
        if replace:
            output = find_and_replace_header(
                text,
                reuse_info,
                template=template,
                template_is_commented=template_is_commented,
                style=comment_style,
                force_multi=force_multi,
                merge_copyrights=merge_copyrights,
            )
        else:
            output = add_new_header(
                text,
                reuse_info,
                template=template,
                template_is_commented=template_is_commented,
                style=comment_style,
                force_multi=force_multi,
                merge_copyrights=merge_copyrights,
            )
    except CommentCreateError:
        out.write(
            _("Error: Could not create comment for '{path}'").format(path=path)
        )
        out.write("\n")
        result = 1
    except MissingReuseInfo:
        out.write(
            _(
                "Error: Generated comment header for '{path}' is missing"
                " copyright lines or license expressions. The template is"
                " probably incorrect. Did not write new header."
            ).format(path=path)
        )
        out.write("\n")
        result = 1
    else:
        with open(path, "w", encoding="utf-8", newline=line_ending) as fp:
            fp.write(output)
        # TODO: This may need to be rephrased more elegantly.
        out.write(_("Successfully changed header of {path}").format(path=path))
        out.write("\n")

    return result


def style_and_unrecognised_warning(args: Namespace) -> None:
    """Log a warning if --style is used together with --skip-unrecognised."""
    if args.style is not None and args.skip_unrecognised:
        _LOGGER.warning(
            _(
                "--skip-unrecognised has no effect when used together with"
                " --style"
            )
        )


def test_mandatory_option_required(args: Namespace) -> None:
    """Raise a parser error if one of the mandatory options is not provided."""
    if not any((args.contributor, args.copyright, args.license)):
        args.parser.error(
            _("option --contributor, --copyright or --license is required")
        )


def all_paths(args: Namespace, project: Project) -> Set[Path]:
    """Return a set of all provided paths, converted into .license paths if they
    exist. If recursive is enabled, all files belonging to *project* are also
    added.
    """
    if args.recursive:
        paths: Set[Path] = set()
        all_files = [path.resolve() for path in project.all_files()]
        for path in args.path:
            if path.is_file():
                paths.add(path)
            else:
                paths |= {
                    child
                    for child in all_files
                    if path.resolve() in child.parents
                }
    else:
        paths = args.path
    return {_determine_license_path(path) for path in paths}


def get_template(
    args: Namespace, project: Project
) -> Tuple[Optional[Template], bool]:
    """If a template is specified on the CLI, find and return it, including
    whether it is a 'commented' template.

    If no template is specified, just return None.
    """
    template: Optional[Template] = None
    commented = False
    if args.template:
        try:
            template = cast(Template, find_template(project, args.template))
        except TemplateNotFound:
            args.parser.error(
                _("template {template} could not be found").format(
                    template=args.template
                )
            )
            # This code is never reached, but mypy is not aware that
            # parser.error quits the program.
            raise

        if ".commented" in Path(cast(str, template.name)).suffixes:
            commented = True
    return template, commented


def get_year(args: Namespace) -> Optional[str]:
    """Get the year. Normally it is today's year. If --year is specified once,
    get that one. If it is specified twice (or more), return the range between
    the two.

    If --exclude-year is specified, return None.
    """
    year = None
    if not args.exclude_year:
        if args.year and len(args.year) > 1:
            year = f"{min(args.year)} - {max(args.year)}"
        elif args.year:
            year = args.year[0]
        else:
            year = str(datetime.date.today().year)
    return year


def get_reuse_info(args: Namespace, year: Optional[str]) -> ReuseInfo:
    """Create a ReuseInfo object from --license, --copyright, and
    --contributor.
    """
    expressions = set(args.license) if args.license is not None else set()
    copyright_prefix = (
        args.copyright_prefix if args.copyright_prefix is not None else "spdx"
    )
    copyright_lines = (
        {
            make_copyright_line(
                item, year=year, copyright_prefix=copyright_prefix
            )
            for item in args.copyright
        }
        if args.copyright is not None
        else set()
    )
    contributors = (
        set(args.contributor) if args.contributor is not None else set()
    )

    return ReuseInfo(
        spdx_expressions=expressions,
        copyright_lines=copyright_lines,
        contributor_lines=contributors,
    )


def verify_write_access(
    paths: Iterable[StrPath], parser: ArgumentParser
) -> None:
    """Raise a parser.error if one of the paths is not writable."""
    not_writeable = [
        str(path) for path in paths if not os.access(path, os.W_OK)
    ]
    if not_writeable:
        parser.error(
            _("can't write to '{}'").format("', '".join(not_writeable))
        )


def verify_paths_comment_style(args: Namespace, paths: Iterable[Path]) -> None:
    """Exit if --style, --force-dot-license, --fallback-dot-license,
    or --skip-unrecognised is not enabled and one of the paths has an
    unrecognised style.
    """
    if (
        not args.style
        and not args.fallback_dot_license
        and not args.skip_unrecognised
        and not args.force_dot_license
    ):
        unrecognised_files = []

        for path in paths:
            if not _has_style(path):
                unrecognised_files.append(path)

        if unrecognised_files:
            args.parser.error(
                "{}\n\n{}".format(
                    _(
                        "The following files do not have a recognised file"
                        " extension. Please use --style, --force-dot-license,"
                        " --fallback-dot-license, or --skip-unrecognised:"
                    ),
                    "\n".join(str(path) for path in unrecognised_files),
                )
            )


def add_arguments(parser: ArgumentParser) -> None:
    """Add arguments to parser."""
    parser.add_argument(
        "--copyright",
        "-c",
        action="append",
        type=str,
        help=_("copyright statement, repeatable"),
    )
    parser.add_argument(
        "--license",
        "-l",
        action="append",
        type=spdx_identifier,
        help=_("SPDX Identifier, repeatable"),
    )
    parser.add_argument(
        "--contributor",
        action="append",
        type=str,
        help=_("file contributor, repeatable"),
    )
    year_mutex_group = parser.add_mutually_exclusive_group()
    year_mutex_group.add_argument(
        "--year",
        "-y",
        action="append",
        type=str,
        help=_("year of copyright statement, optional"),
    )
    parser.add_argument(
        "--style",
        "-s",
        action="store",
        type=str,
        choices=list(NAME_STYLE_MAP),
        help=_("comment style to use, optional"),
    )
    parser.add_argument(
        "--copyright-prefix",
        action="store",
        choices=list(_COPYRIGHT_PREFIXES.keys()),
        help=_("copyright prefix to use, optional"),
    )
    parser.add_argument(
        "--copyright-style",
        action="store",
        dest="copyright_prefix",
        help=SUPPRESS,
    )
    parser.add_argument(
        "--template",
        "-t",
        action="store",
        type=str,
        help=_("name of template to use, optional"),
    )
    year_mutex_group.add_argument(
        "--exclude-year",
        action="store_true",
        help=_("do not include year in statement"),
    )
    parser.add_argument(
        "--merge-copyrights",
        action="store_true",
        help=_("merge copyright lines if copyright statements are identical"),
    )
    line_mutex_group = parser.add_mutually_exclusive_group()
    line_mutex_group.add_argument(
        "--single-line",
        action="store_true",
        help=_("force single-line comment style, optional"),
    )
    line_mutex_group.add_argument(
        "--multi-line",
        action="store_true",
        help=_("force multi-line comment style, optional"),
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help=_(
            "add headers to all files under specified directories recursively"
        ),
    )
    parser.add_argument(
        "--no-replace",
        action="store_true",
        help=_(
            "do not replace the first header in the file; just add a new one"
        ),
    )
    style_mutex_group = parser.add_mutually_exclusive_group()
    style_mutex_group.add_argument(
        "--force-dot-license",
        action="store_true",
        help=_(
            "always write a .license file instead of a header inside the file"
        ),
    )
    style_mutex_group.add_argument(
        "--fallback-dot-license",
        action="store_true",
        help=_(
            "write a .license file to files with unrecognised comment styles"
        ),
    )
    style_mutex_group.add_argument(
        "--skip-unrecognised",
        action="store_true",
        help=_("skip files with unrecognised comment styles"),
    )
    style_mutex_group.add_argument(
        "--skip-unrecognized",
        dest="skip_unrecognised",
        action="store_true",
        help=SUPPRESS,
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help=_("skip files that already contain REUSE information"),
    )
    parser.add_argument("path", action="store", nargs="+", type=PathType("r"))


def run(args: Namespace, project: Project, out: IO[str] = sys.stdout) -> int:
    """Add headers to files."""
    test_mandatory_option_required(args)

    style_and_unrecognised_warning(args)

    paths = all_paths(args, project)

    verify_paths_comment_style(args, paths)

    if not args.force_dot_license:
        verify_write_access(paths, args.parser)

    # Verify line handling and comment styles before proceeding
    verify_paths_line_handling(args, paths)

    template, commented = get_template(args, project)

    year = get_year(args)

    reuse_info = get_reuse_info(args, year)

    result = 0
    for path in paths:
        binary = is_binary(str(path))
        if binary or _is_uncommentable(path) or args.force_dot_license:
            new_path = _determine_license_suffix_path(path)
            if binary:
                _LOGGER.info(
                    _(
                        "'{path}' is a binary, therefore using '{new_path}'"
                        " for the header"
                    ).format(path=path, new_path=new_path)
                )
            path = Path(new_path)
            path.touch()
        result += add_header_to_file(
            path=path,
            reuse_info=reuse_info,
            template=template,
            template_is_commented=commented,
            style=args.style,
            force_multi=args.multi_line,
            skip_existing=args.skip_existing,
            skip_unrecognised=args.skip_unrecognised,
            fallback_dot_license=args.fallback_dot_license,
            merge_copyrights=args.merge_copyrights,
            replace=not args.no_replace,
            out=out,
        )

    return min(result, 1)
