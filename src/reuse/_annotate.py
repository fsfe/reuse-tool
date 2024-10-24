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

import logging
import sys
from typing import IO, Optional, Type, cast

from jinja2 import Environment, FileSystemLoader, Template
from jinja2.exceptions import TemplateNotFound

from . import ReuseInfo
from ._util import _determine_license_suffix_path
from .comment import (
    NAME_STYLE_MAP,
    CommentStyle,
    EmptyCommentStyle,
    get_comment_style,
)
from .exceptions import CommentCreateError, MissingReuseInfoError
from .extract import contains_reuse_info, detect_line_endings
from .header import add_new_header, find_and_replace_header
from .i18n import _
from .project import Project
from .types import StrPath

_LOGGER = logging.getLogger(__name__)


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
        comment_style = get_comment_style(path)
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
    except MissingReuseInfoError:
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
