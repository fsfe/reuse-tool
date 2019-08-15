# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Functions for manipulating the comment headers of files."""

import datetime
import logging
import sys
from gettext import gettext as _
from pathlib import Path

from boolean.boolean import ParseError
from jinja2 import Environment, FileSystemLoader, PackageLoader, Template
from jinja2.exceptions import TemplateNotFound
from license_expression import ExpressionError

from . import SpdxInfo
from ._comment import (
    COMMENT_STYLE_MAP,
    NAME_STYLE_MAP,
    CommentCreateError,
    CommentParseError,
    CommentStyle,
    PythonCommentStyle,
)
from ._util import (
    PathType,
    extract_spdx_info,
    make_copyright_line,
    spdx_identifier,
)
from .project import create_project

_LOGGER = logging.getLogger(__name__)

_ENV = Environment(
    loader=PackageLoader("reuse", "templates"), trim_blocks=True
)
DEFAULT_TEMPLATE = _ENV.get_template("default_template.jinja2")


class MissingSpdxInfo(Exception):
    """Some SPDX information is missing from the result."""


# TODO: Add a template here maybe.
def _create_new_header(
    spdx_info: SpdxInfo,
    template: Template = None,
    template_is_commented: bool = False,
    style: CommentStyle = None,
) -> str:
    """Format a new header from scratch.

    :raises CommentCreateError: if a comment could not be created.
    :raises MissingSpdxInfo: if the generated comment is missing SPDX
        information.
    """
    if template is None:
        template = DEFAULT_TEMPLATE
    if style is None:
        style = PythonCommentStyle

    rendered = template.render(
        copyright_lines=sorted(spdx_info.copyright_lines),
        spdx_expressions=sorted(map(str, spdx_info.spdx_expressions)),
    )

    if template_is_commented:
        result = rendered.strip("\n")
    else:
        result = style.create_comment(rendered).strip("\n")

    # Verify that the result contains all SpdxInfo.
    new_spdx_info = extract_spdx_info(result)
    if (
        spdx_info.copyright_lines != new_spdx_info.copyright_lines
        and spdx_info.spdx_expressions != new_spdx_info.spdx_expressions
    ):
        _LOGGER.debug(
            _(
                "generated comment is missing copyright lines or license "
                "expressions"
            )
        )
        raise MissingSpdxInfo()

    return result


def create_header(
    spdx_info: SpdxInfo,
    header: str = None,
    template: Template = None,
    template_is_commented: bool = False,
    style: CommentStyle = None,
) -> str:
    """Create a header containing *spdx_info*. *header* is an optional argument
    containing a header which should be modified to include *spdx_info*. If
    *header* is not given, a brand new header is created.

    *template*, *template_is_commented*, and *style* determine what the header
    will look like, and whether it will be commented or not.

    :raises CommentCreateError: if a comment could not be created.
    :raises MissingSpdxInfo: if the generated comment is missing SPDX
        information.
    """
    if template is None:
        template = DEFAULT_TEMPLATE
    if style is None:
        style = PythonCommentStyle

    new_header = ""
    if header:
        try:
            existing_spdx = extract_spdx_info(header)
        except (ExpressionError, ParseError) as err:
            raise CommentCreateError(
                "existing header contains an erroneous SPDX expression"
            ) from err

        # TODO: This behaviour does not match the docstring.
        spdx_info = SpdxInfo(
            spdx_info.spdx_expressions.union(existing_spdx.spdx_expressions),
            spdx_info.copyright_lines.union(existing_spdx.copyright_lines),
        )

        if header.startswith("#!"):
            new_header = header.split("\n")[0] + "\n"

    new_header += _create_new_header(
        spdx_info,
        template=template,
        template_is_commented=template_is_commented,
        style=style,
    )
    return new_header


def find_and_replace_header(
    text: str,
    spdx_info: SpdxInfo,
    template: Template = None,
    template_is_commented: bool = False,
    style: CommentStyle = None,
) -> str:
    """Find the comment block starting at the first character in *text*. That
    comment block is replaced by a new comment block containing *spdx_info*. It
    is formatted as according to *template*. The template is normally
    uncommented, but if it is already commented, *template_is_commented* should
    be :const:`True`.

    If both *style* and *template_is_commented* are provided, *style* is only
    used to find the header comment.

    If the comment block already contained some SPDX information, that
    information is merged into *spdx_info*.

    If no header exists, one is simply created.

    *text* is returned with a new header.

    :raises CommentCreateError: if a comment could not be created.
    :raises MissingSpdxInfo: if the generated comment is missing SPDX
        information.
    """
    if template is None:
        template = DEFAULT_TEMPLATE
    if style is None:
        style = PythonCommentStyle

    try:
        header = style.comment_at_first_character(text)
    except CommentParseError:
        # TODO: Log this
        header = ""

    # TODO: This is a duplicated check that also happens inside of
    # create_header.
    try:
        existing_spdx = extract_spdx_info(header)
    except (ExpressionError, ParseError):
        # This error is handled in create_header. Just set the value to None
        # here to satisfy the linter.
        existing_spdx = None

    new_header = create_header(
        spdx_info,
        header,
        template=template,
        template_is_commented=template_is_commented,
        style=style,
    )

    if header and any(existing_spdx):
        text = text.replace(header, "", 1)
    else:
        # Some extra spacing for the new header.
        new_header = new_header + "\n"
        if not text.startswith("\n"):
            new_header = new_header + "\n"

    return new_header + text


def _verify_paths_supported(paths, parser):
    for path in paths:
        try:
            COMMENT_STYLE_MAP[path.suffix]
        except KeyError:
            parser.error(
                _(
                    "'{}' does not have a recognised file extension, "
                    "please use --style".format(path)
                )
            )


def _find_template(name: str) -> Template:
    """Find a template given a name.

    :raises TemplateNotFound: if template could not be found.
    """
    project = create_project()
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


def add_arguments(parser) -> None:
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
        "--year",
        "-y",
        action="store",
        type=str,
        help=_("year of copyright statement, optional"),
    )
    parser.add_argument(
        "--style",
        "-s",
        action="store",
        type=str,
        choices=list(NAME_STYLE_MAP),
        help=_("comment style to use"),
    )
    parser.add_argument(
        "--template",
        "-t",
        action="store",
        type=str,
        help=_("name of template to use"),
    )
    parser.add_argument(
        "--exclude-year",
        action="store_true",
        help=_("do not include current or specified year in statement"),
    )
    parser.add_argument("path", action="store", nargs="+", type=PathType("w"))


def run(args, out=sys.stdout) -> int:
    """Add headers to files."""
    if not any((args.copyright, args.license)):
        args.parser.error(_("option --copyright or --license is required"))

    if args.exclude_year and args.year:
        args.parser.error(
            _("option --exclude-year and --year are mutually exclusive")
        )

    # First loop to verify before proceeding
    if args.style is None:
        _verify_paths_supported(args.path, args.parser)

    template = None
    commented = False
    if args.template:
        try:
            template = _find_template(args.template)
        except TemplateNotFound:
            args.parser.error(
                _("template {template} could not be found").format(
                    template=args.template
                )
            )

        if ".commented" in Path(template.name).suffixes:
            commented = True

    year = None
    if not args.exclude_year:
        if args.year:
            year = args.year
        else:
            year = datetime.date.today().year

    expressions = set(args.license) if args.license is not None else set()
    copyright_lines = (
        set(make_copyright_line(x, year=year) for x in args.copyright)
        if args.copyright is not None
        else set()
    )

    spdx_info = SpdxInfo(expressions, copyright_lines)

    result = 0
    for path in args.path:
        if args.style is not None:
            style = NAME_STYLE_MAP[args.style]
        else:
            style = COMMENT_STYLE_MAP[path.suffix]

        with path.open("r") as fp:
            text = fp.read()

        try:
            output = find_and_replace_header(
                text,
                spdx_info,
                template=template,
                template_is_commented=commented,
                style=style,
            )
        except CommentCreateError:
            out.write(
                _("Error: Could not create comment for '{path}'").format(
                    path=path
                )
            )
            out.write("\n")
            result = 1
        except MissingSpdxInfo:
            out.write(
                _(
                    "Error: Generated comment header for '{path}' is missing "
                    "copyright lines or license expressions. The template is "
                    "probably incorrect. Did not write new header."
                ).format(path=path)
            )
            out.write("\n")
            result = 1
        else:
            with path.open("w") as fp:
                fp.write(output)
            # TODO: This may need to be rephrased more elegantly.
            out.write(
                _("Successfully changed header of {path}").format(path=path)
            )

    return result
