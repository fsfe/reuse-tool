# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2024 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
# SPDX-FileCopyrightText: 2024 Kerry McAdams <github@klmcadams>
# SPDX-FileCopyrightText: 2024 Emil Velikov <emil.l.velikov@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Entry functions for reuse."""

import argparse
import contextlib
import logging
import os
import sys
import warnings
from gettext import gettext as _
from pathlib import Path
from types import ModuleType
from typing import IO, Callable, Optional, Type, cast

from . import (
    __REUSE_version__,
    __version__,
    _annotate,
    _lint_file,
    convert_dep5,
    download,
    lint,
    spdx,
    supported_licenses,
)
from ._format import INDENT, fill_all, fill_paragraph
from ._util import PathType, setup_logging
from .global_licensing import GlobalLicensingParseError
from .project import GlobalLicensingConflict, Project
from .vcs import find_root

shtab: Optional[ModuleType] = None
with contextlib.suppress(ImportError):
    import shtab  # type: ignore[no-redef,import-not-found]

_LOGGER = logging.getLogger(__name__)

_DESCRIPTION_LINES = [
    _(
        "reuse is a tool for compliance with the REUSE"
        " recommendations. See <https://reuse.software/> for more"
        " information, and <https://reuse.readthedocs.io/> for the online"
        " documentation."
    ),
    _(
        "This version of reuse is compatible with version {} of the REUSE"
        " Specification."
    ).format(__REUSE_version__),
    _("Support the FSFE's work:"),
]

_INDENTED_LINE = _(
    "Donations are critical to our strength and autonomy. They enable us to"
    " continue working for Free Software wherever necessary. Please consider"
    " making a donation at <https://fsfe.org/donate/>."
)

_DESCRIPTION_TEXT = (
    fill_all("\n\n".join(_DESCRIPTION_LINES))
    + "\n\n"
    + fill_paragraph(_INDENTED_LINE, indent_width=INDENT)
)

_EPILOG_TEXT = ""


def parser() -> argparse.ArgumentParser:
    """Create the parser and return it."""
    # pylint: disable=redefined-outer-name
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description=_DESCRIPTION_TEXT,
        epilog=_EPILOG_TEXT,
    )
    parser.add_argument(
        "--debug", action="store_true", help=_("enable debug statements")
    )
    parser.add_argument(
        "--suppress-deprecation",
        action="store_true",
        help=_("hide deprecation warnings"),
    )
    parser.add_argument(
        "--include-submodules",
        action="store_true",
        help=_("do not skip over Git submodules"),
    )
    parser.add_argument(
        "--include-meson-subprojects",
        action="store_true",
        help=_("do not skip over Meson subprojects"),
    )
    parser.add_argument(
        "--no-multiprocessing",
        action="store_true",
        help=_("do not use multiprocessing"),
    )
    parser.add_argument(
        "--root",
        action="store",
        metavar="PATH",
        type=PathType("r", force_directory=True),
        help=_("define root of project"),
    )
    if shtab:
        # This is magic. Running `reuse -s bash` now prints bash completions.
        shtab.add_argument_to(parser, ["-s", "--print-completion"])
    parser.add_argument(
        "--version",
        action="store_true",
        help=_("show program's version number and exit"),
    )
    parser.set_defaults(func=lambda *args: parser.print_help())

    subparsers = parser.add_subparsers(title=_("subcommands"))

    add_command(
        subparsers,
        "annotate",
        _annotate.add_arguments,
        _annotate.run,
        help=_("add copyright and licensing into the header of files"),
        description=fill_all(
            _(
                "Add copyright and licensing into the header of one or more"
                " files.\n"
                "\n"
                "By using --copyright and --license, you can specify which"
                " copyright holders and licenses to add to the headers of the"
                " given files.\n"
                "\n"
                "By using --contributor, you can specify people or entity that"
                " contributed but are not copyright holder of the given"
                " files."
            )
        ),
    )

    add_command(
        subparsers,
        "download",
        download.add_arguments,
        download.run,
        help=_("download a license and place it in the LICENSES/ directory"),
        description=fill_all(
            _("Download a license and place it in the LICENSES/ directory.")
        ),
    )

    add_command(
        subparsers,
        "lint",
        lint.add_arguments,
        lint.run,
        help=_("list all non-compliant files"),
        description=fill_all(
            _(
                "Lint the project directory for compliance with"
                " version {reuse_version} of the REUSE Specification. You can"
                " find the latest version of the specification at"
                " <https://reuse.software/spec/>.\n"
                "\n"
                "Specifically, the following criteria are checked:\n"
                "\n"
                "- Are there any bad (unrecognised, not compliant with SPDX)"
                " licenses in the project?\n"
                "\n"
                "- Are there any deprecated licenses in the project?\n"
                "\n"
                "- Are there any license files in the LICENSES/ directory"
                " without file extension?\n"
                "\n"
                "- Are any licenses referred to inside of the project, but"
                " not included in the LICENSES/ directory?\n"
                "\n"
                "- Are any licenses included in the LICENSES/ directory that"
                " are not used inside of the project?\n"
                "\n"
                "- Are there any read errors?\n"
                "\n"
                "- Do all files have valid copyright and licensing"
                " information?"
            ).format(reuse_version=__REUSE_version__)
        ),
    )

    add_command(
        subparsers,
        "lint-file",
        _lint_file.add_arguments,
        _lint_file.run,
        description=fill_all(
            _(
                "Lint individual files. The specified files are checked for"
                " the presence of copyright and licensing information, and"
                " whether  the found licenses are included in the LICENSES/"
                " directory."
            )
        ),
        help=_("list non-compliant files from specified list of files"),
    )

    add_command(
        subparsers,
        "spdx",
        spdx.add_arguments,
        spdx.run,
        description=fill_all(
            _("Generate an SPDX bill of materials in RDF format.")
        ),
        help=_("print the project's bill of materials in SPDX format"),
    )

    add_command(
        subparsers,
        "supported-licenses",
        supported_licenses.add_arguments,
        supported_licenses.run,
        description=fill_all(
            _("List all non-deprecated SPDX licenses from the official list.")
        ),
        help=_("list all supported SPDX licenses"),
        aliases=["supported-licences"],
    )

    add_command(
        subparsers,
        "convert-dep5",
        convert_dep5.add_arguments,
        convert_dep5.run,
        description=fill_all(
            _(
                "Convert .reuse/dep5 into a REUSE.toml file in your project"
                " root. The generated file is semantically identical. The"
                " .reuse/dep5 file is subsequently deleted."
            )
        ),
        help=_("convert .reuse/dep5 to REUSE.toml"),
    )

    return parser


def add_command(  # pylint: disable=too-many-arguments,redefined-builtin
    subparsers: argparse._SubParsersAction,
    name: str,
    add_arguments_func: Callable[[argparse.ArgumentParser], None],
    run_func: Callable[[argparse.Namespace, Project, IO[str]], int],
    formatter_class: Optional[Type[argparse.HelpFormatter]] = None,
    description: Optional[str] = None,
    help: Optional[str] = None,
    aliases: Optional[list[str]] = None,
) -> None:
    """Add a subparser for a command."""
    if formatter_class is None:
        formatter_class = argparse.RawTextHelpFormatter
    subparser = subparsers.add_parser(
        name,
        formatter_class=formatter_class,
        description=description,
        help=help,
        aliases=aliases or [],
    )
    add_arguments_func(subparser)
    subparser.set_defaults(func=run_func)
    subparser.set_defaults(parser=subparser)


def main(args: Optional[list[str]] = None, out: IO[str] = sys.stdout) -> int:
    """Main entry function."""
    if args is None:
        args = cast(list[str], sys.argv[1:])

    main_parser = parser()
    parsed_args = main_parser.parse_args(args)

    setup_logging(level=logging.DEBUG if parsed_args.debug else logging.WARNING)
    # Show all warnings raised by ourselves.
    if not parsed_args.suppress_deprecation:
        warnings.filterwarnings("default", module="reuse")

    if parsed_args.version:
        out.write(f"reuse {__version__}\n")
        return 0

    # Very stupid workaround to not print a DEP5 deprecation warning in the
    # middle of conversion to REUSE.toml.
    if args and args[0] == "convert-dep5":
        os.environ["_SUPPRESS_DEP5_WARNING"] = "1"

    root = parsed_args.root
    if root is None:
        root = find_root()
    if root is None:
        root = Path.cwd()
    try:
        project = Project.from_directory(root)
    # FileNotFoundError and NotADirectoryError don't need to be caught because
    # argparse already made sure of these things.
    except GlobalLicensingParseError as error:
        main_parser.error(
            _(
                "'{path}' could not be parsed. We received the following error"
                " message: {message}"
            ).format(path=error.source, message=str(error))
        )
    except GlobalLicensingConflict as error:
        main_parser.error(str(error))
    except OSError as error:
        main_parser.error(str(error))

    project.include_submodules = parsed_args.include_submodules
    project.include_meson_subprojects = parsed_args.include_meson_subprojects

    return parsed_args.func(parsed_args, project, out)


if __name__ == "__main__":
    sys.exit(main())
