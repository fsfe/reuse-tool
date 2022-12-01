# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2019 Stefan Bakker <s.bakker777@gmail.com>
# SPDX-FileCopyrightText: 2019 Kirill Elagin <kirelagin@gmail.com>
# SPDX-FileCopyrightText: 2020 Dmitry Bogatov
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
# SPDX-FileCopyrightText: 2021 Alvar Penning
# SPDX-FileCopyrightText: 2021 Alliander N.V. <https://alliander.com>
# SPDX-FileCopyrightText: 2021 Robin Vobruba <hoijui.quaero@gmail.com>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2022 Yaman Qalieh
# SPDX-FileCopyrightText: 2022 Carmen Bianca Bakker <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Functions for manipulating the comment headers of files."""


import argparse
import datetime
import logging
import os
import re
import sys
from argparse import ArgumentParser
from gettext import gettext as _
from os import PathLike
from pathlib import Path
from typing import Iterable, List, NamedTuple, Optional, Sequence, Tuple

from binaryornot.check import is_binary
from boolean.boolean import ParseError
from jinja2 import Environment, FileSystemLoader, PackageLoader, Template
from jinja2.exceptions import TemplateNotFound
from license_expression import ExpressionError

from . import SpdxInfo
from ._comment import (
    EXTENSION_COMMENT_STYLE_MAP_LOWERCASE,
    FILENAME_COMMENT_STYLE_MAP_LOWERCASE,
    NAME_STYLE_MAP,
    CommentCreateError,
    CommentParseError,
    CommentStyle,
    EmptyCommentStyle,
    PythonCommentStyle,
    UncommentableCommentStyle,
)
from ._util import (
    _COPYRIGHT_STYLES,
    PathType,
    _determine_license_path,
    _determine_license_suffix_path,
    contains_spdx_info,
    detect_line_endings,
    extract_spdx_info,
    make_copyright_line,
    merge_copyright_lines,
    spdx_identifier,
)
from .project import Project

_LOGGER = logging.getLogger(__name__)

_ENV = Environment(loader=PackageLoader("reuse", "templates"), trim_blocks=True)
DEFAULT_TEMPLATE = _ENV.get_template("default_template.jinja2")

_NEWLINE_PATTERN = re.compile(r"\n", re.MULTILINE)


class _TextSections(NamedTuple):
    """Used to split up text in three parts."""

    before: str
    middle: str
    after: str


class MissingSpdxInfo(Exception):
    """Some SPDX information is missing from the result."""


# TODO: Add a template here maybe.
def _create_new_header(
    spdx_info: SpdxInfo,
    template: Template = None,
    template_is_commented: bool = False,
    style: CommentStyle = None,
    force_multi: bool = False,
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
    ).strip("\n")

    if template_is_commented:
        result = rendered
    else:
        result = style.create_comment(rendered, force_multi=force_multi).strip(
            "\n"
        )

    # Verify that the result contains all SpdxInfo.
    new_spdx_info = extract_spdx_info(result)
    if (
        spdx_info.copyright_lines != new_spdx_info.copyright_lines
        and spdx_info.spdx_expressions != new_spdx_info.spdx_expressions
    ):
        _LOGGER.debug(
            _(
                "generated comment is missing copyright lines or license"
                " expressions"
            )
        )
        _LOGGER.debug(result)
        raise MissingSpdxInfo()

    return result


# pylint: disable=too-many-arguments
def create_header(
    spdx_info: SpdxInfo,
    header: str = None,
    template: Template = None,
    template_is_commented: bool = False,
    style: CommentStyle = None,
    force_multi: bool = False,
    merge_copyrights: bool = False,
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

        if merge_copyrights:
            spdx_copyrights = merge_copyright_lines(
                spdx_info.copyright_lines.union(existing_spdx.copyright_lines),
            )
        else:
            spdx_copyrights = spdx_info.copyright_lines.union(
                existing_spdx.copyright_lines
            )

        # TODO: This behaviour does not match the docstring.
        spdx_info = SpdxInfo(
            spdx_info.spdx_expressions.union(existing_spdx.spdx_expressions),
            spdx_copyrights,
        )

    new_header += _create_new_header(
        spdx_info,
        template=template,
        template_is_commented=template_is_commented,
        style=style,
        force_multi=force_multi,
    )
    return new_header


def _indices_of_newlines(text: str) -> Sequence[int]:
    indices = [0]
    start = 0

    while True:
        match = _NEWLINE_PATTERN.search(text, start)
        if match:
            start = match.span()[1]
            indices.append(start)
        else:
            break

    return indices


def _find_first_spdx_comment(
    text: str, style: CommentStyle = None
) -> _TextSections:
    """Find the first SPDX comment in the file. Return a tuple with everything
    preceding the comment, the comment itself, and everything following it.

    :raises MissingSpdxInfo: if no SPDX info can be found in any comment
    """
    if style is None:
        style = PythonCommentStyle

    indices = _indices_of_newlines(text)

    for index in indices:
        try:
            comment = style.comment_at_first_character(text[index:])
        except CommentParseError:
            continue
        if contains_spdx_info(comment):
            return _TextSections(
                text[:index], comment + "\n", text[index + len(comment) + 1 :]
            )

    raise MissingSpdxInfo()


def _extract_shebang(prefix: str, text: str) -> Tuple[str, str]:
    """Remove all lines that start with the shebang prefix from *text*. Return a
    tuple of (shebang, reduced_text).
    """
    shebang_lines = []
    for line in text.splitlines():
        if line.startswith(prefix):
            shebang_lines.append(line)
            text = text.replace(line, "", 1)
        else:
            shebang = "\n".join(shebang_lines)
            break
    return (shebang, text)


# pylint: disable=too-many-arguments
def find_and_replace_header(
    text: str,
    spdx_info: SpdxInfo,
    template: Template = None,
    template_is_commented: bool = False,
    style: CommentStyle = None,
    force_multi: bool = False,
    merge_copyrights: bool = False,
) -> str:
    """Find the first SPDX comment block in *text*. That comment block is
    replaced by a new comment block containing *spdx_info*. It is formatted as
    according to *template*. The template is normally uncommented, but if it is
    already commented, *template_is_commented* should be :const:`True`.

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
    if style is None:
        style = PythonCommentStyle

    try:
        before, header, after = _find_first_spdx_comment(text, style=style)
    except MissingSpdxInfo:
        before, header, after = "", "", text

    # Workaround. EmptyCommentStyle should always be completely replaced.
    if style is EmptyCommentStyle:
        after = ""

    _LOGGER.debug(f"before = {repr(before)}")
    _LOGGER.debug(f"header = {repr(header)}")
    _LOGGER.debug(f"after = {repr(after)}")

    # Keep special first-line-of-file lines as the first line in the file,
    # or say, move our comments after it.
    if style.SHEBANGS:
        for shebang in style.SHEBANGS:
            # Extract shebang from header and put it in before. It's a bit
            # messy, but it ends up working.
            if header.startswith(shebang) and not before.strip():
                before, header = _extract_shebang(shebang, header)
            elif after.startswith(shebang) and not any((before, header)):
                before, after = _extract_shebang(shebang, after)
            else:
                continue
            break

    header = create_header(
        spdx_info,
        header,
        template=template,
        template_is_commented=template_is_commented,
        style=style,
        force_multi=force_multi,
        merge_copyrights=merge_copyrights,
    )

    new_text = f"{header}\n"
    if before.strip():
        new_text = f"{before.rstrip()}\n\n{new_text}"
    if after.strip():
        new_text = f"{new_text}\n{after.lstrip()}"
    return new_text


# pylint: disable=too-many-arguments
def add_new_header(
    text: str,
    spdx_info: SpdxInfo,
    template: Template = None,
    template_is_commented: bool = False,
    style: CommentStyle = None,
    force_multi: bool = False,
    merge_copyrights: bool = False,
) -> str:
    """Add a new header at the very top of *text*, similar to
    find_and_replace_header. But in this function, do not replace any headers or
    search for any existing SPDX information.

    :raises CommentCreateError: if a comment could not be created.
    """
    if style is None:
        style = PythonCommentStyle

    shebang = ""

    if style.SHEBANGS:
        for shebang_prefix in style.SHEBANGS:
            if text.startswith(shebang_prefix):
                shebang, text = _extract_shebang(shebang_prefix, text)
                break

    header = create_header(
        spdx_info,
        None,
        template=template,
        template_is_commented=template_is_commented,
        style=style,
        force_multi=force_multi,
        merge_copyrights=merge_copyrights,
    )

    new_text = f"{header}\n"
    if shebang.strip():
        new_text = f"{shebang.rstrip()}\n\n{new_text}"
    if text.strip():
        new_text = f"{new_text}\n{text.lstrip()}"
    return new_text


def _get_comment_style(path: Path) -> Optional[CommentStyle]:
    """Return value of CommentStyle detected for *path* or None."""
    style = FILENAME_COMMENT_STYLE_MAP_LOWERCASE.get(path.name.lower())
    if style is None:
        style = EXTENSION_COMMENT_STYLE_MAP_LOWERCASE.get(path.suffix.lower())
    return style


def _is_uncommentable(path: Path) -> bool:
    """Determines if *path* is uncommentable, e.g., the file is a binary or
    registered as an UncommentableCommentStyle.
    """
    is_uncommentable = _get_comment_style(path) == UncommentableCommentStyle
    return is_uncommentable or is_binary(str(path))


def _verify_paths_line_handling(
    paths: List[Path],
    parser: ArgumentParser,
    force_single: bool,
    force_multi: bool,
):
    """This function aborts the parser when *force_single* or *force_multi* is
    used, but the file type does not support that type of comment style.
    """
    for path in paths:
        style = _get_comment_style(path)
        if style is None:
            continue
        if force_single and not style.can_handle_single():
            parser.error(
                _(
                    "'{path}' does not support single-line comments, please"
                    " do not use --single-line"
                ).format(path=path)
            )
        if force_multi and not style.can_handle_multi():
            parser.error(
                _(
                    "'{path}' does not support multi-line comments, please"
                    " do not use --multi-line"
                ).format(path=path)
            )


def _verify_paths_comment_style(paths: List[Path], parser: ArgumentParser):
    unrecognised_files = []

    for path in paths:
        style = _get_comment_style(path)
        not_uncommentable = not _is_uncommentable(path)

        # TODO: This check is duplicated.
        if style is None and not_uncommentable:
            unrecognised_files.append(path)

    if unrecognised_files:
        parser.error(
            "{}\n{}".format(
                _(
                    "The following files do not have a recognised file"
                    " extension. Please use --style, --force-dot-license or"
                    " --skip-unrecognised:"
                ),
                "\n".join(str(path) for path in unrecognised_files),
            )
        )


def _find_template(project: Project, name: str) -> Template:
    """Find a template given a name.

    :raises TemplateNotFound: if template could not be found.
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


def _add_header_to_file(
    path: PathLike,
    spdx_info: SpdxInfo,
    template: Template,
    template_is_commented: bool,
    style: Optional[str],
    force_multi: bool = False,
    skip_existing: bool = False,
    merge_copyrights: bool = False,
    replace: bool = True,
    out=sys.stdout,
) -> int:
    """Helper function."""
    # pylint: disable=too-many-arguments
    result = 0
    if style is not None:
        style = NAME_STYLE_MAP[style]
    else:
        style = _get_comment_style(path)
        if style is None:
            out.write(_("Skipped unrecognised file {path}").format(path=path))
            out.write("\n")
            return result

    with path.open("r", encoding="utf-8", newline="") as fp:
        text = fp.read()

    # Ideally, this check is done elsewhere. But that would necessitate reading
    # the file contents before this function is called.
    if skip_existing and contains_spdx_info(text):
        out.write(
            _(
                "Skipped file '{path}' already containing SPDX information"
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
                spdx_info,
                template=template,
                template_is_commented=template_is_commented,
                style=style,
                force_multi=force_multi,
                merge_copyrights=merge_copyrights,
            )
        else:
            output = add_new_header(
                text,
                spdx_info,
                template=template,
                template_is_commented=template_is_commented,
                style=style,
                force_multi=force_multi,
                merge_copyrights=merge_copyrights,
            )
    except CommentCreateError:
        out.write(
            _("Error: Could not create comment for '{path}'").format(path=path)
        )
        out.write("\n")
        result = 1
    except MissingSpdxInfo:
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
        with path.open("w", encoding="utf-8", newline=line_ending) as fp:
            fp.write(output)
        # TODO: This may need to be rephrased more elegantly.
        out.write(_("Successfully changed header of {path}").format(path=path))
        out.write("\n")

    return result


def _verify_write_access(paths: Iterable[PathLike], parser: ArgumentParser):
    not_writeable = [
        str(path) for path in paths if not os.access(path, os.W_OK)
    ]
    if not_writeable:
        parser.error(
            _("can't write to '{}'").format("', '".join(not_writeable))
        )


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
        "--copyright-style",
        action="store",
        choices=list(_COPYRIGHT_STYLES.keys()),
        help=_("copyright style to use, optional"),
    )
    parser.add_argument(
        "--template",
        "-t",
        action="store",
        type=str,
        help=_("name of template to use, optional"),
    )
    parser.add_argument(
        "--exclude-year",
        action="store_true",
        help=_("do not include year in statement"),
    )
    parser.add_argument(
        "--merge-copyrights",
        action="store_true",
        help=_("merge copyright lines if copyright statements are identical"),
    )
    parser.add_argument(
        "--single-line",
        action="store_true",
        help=_("force single-line comment style, optional"),
    )
    parser.add_argument(
        "--multi-line",
        action="store_true",
        help=_("force multi-line comment style, optional"),
    )
    parser.add_argument(
        "--explicit-license",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--force-dot-license",
        action="store_true",
        help=_("write a .license file instead of a header inside the file"),
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
    parser.add_argument(
        "--skip-unrecognised",
        action="store_true",
        help=_("skip files with unrecognised comment styles"),
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help=_("skip files that already contain SPDX information"),
    )
    parser.add_argument("path", action="store", nargs="+", type=PathType("r"))


def run(args, project: Project, out=sys.stdout) -> int:
    """Add headers to files."""
    # pylint: disable=too-many-branches,too-many-locals,too-many-statements
    if "addheader" in args.parser.prog.split():
        _LOGGER.warning(
            _(
                "'reuse addheader' has been deprecated in favour of"
                " 'reuse annotate'"
            )
        )

    if not any((args.copyright, args.license)):
        args.parser.error(_("option --copyright or --license is required"))

    if args.exclude_year and args.year:
        args.parser.error(
            _("option --exclude-year and --year are mutually exclusive")
        )

    if args.single_line and args.multi_line:
        args.parser.error(
            _("option --single-line and --multi-line are mutually exclusive")
        )

    if args.style is not None and args.skip_unrecognised:
        _LOGGER.warning(
            _(
                "--skip-unrecognised has no effect when used together with"
                " --style"
            )
        )
    if args.explicit_license:
        _LOGGER.warning(
            _(
                "--explicit-license has been deprecated in favour of"
                " --force-dot-license"
            )
        )
        args.force_dot_license = True

    if args.recursive:
        paths = set()
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

    paths = {_determine_license_path(path) for path in paths}

    if not args.force_dot_license:
        _verify_write_access(paths, args.parser)

    # Verify line handling and comment styles before proceeding
    if args.style is None and not args.force_dot_license:
        _verify_paths_line_handling(
            paths,
            args.parser,
            force_single=args.single_line,
            force_multi=args.multi_line,
        )
        if not args.skip_unrecognised:
            _verify_paths_comment_style(paths, args.parser)

    template = None
    commented = False
    if args.template:
        try:
            template = _find_template(project, args.template)
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
        if args.year and len(args.year) > 1:
            year = f"{min(args.year)} - {max(args.year)}"
        elif args.year:
            year = args.year.pop()
        else:
            year = datetime.date.today().year

    expressions = set(args.license) if args.license is not None else set()
    copyright_style = (
        args.copyright_style if args.copyright_style is not None else "spdx"
    )
    copyright_lines = (
        {
            make_copyright_line(x, year=year, copyright_style=copyright_style)
            for x in args.copyright
        }
        if args.copyright is not None
        else set()
    )

    spdx_info = SpdxInfo(expressions, copyright_lines)

    result = 0
    for path in paths:
        uncommentable = _is_uncommentable(path)
        if uncommentable or args.force_dot_license:
            new_path = _determine_license_suffix_path(path)
            if uncommentable:
                _LOGGER.info(
                    _(
                        "'{path}' is a binary, therefore using '{new_path}'"
                        " for the header"
                    ).format(path=path, new_path=new_path)
                )
            path = Path(new_path)
            path.touch()
        result += _add_header_to_file(
            path=path,
            spdx_info=spdx_info,
            template=template,
            template_is_commented=commented,
            style=args.style,
            force_multi=args.multi_line,
            skip_existing=args.skip_existing,
            merge_copyrights=args.merge_copyrights,
            replace=not args.no_replace,
            out=out,
        )

    return min(result, 1)
