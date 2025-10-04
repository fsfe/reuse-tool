# SPDX-FileCopyrightText: 2024 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Utilities that are common to multiple CLI commands."""

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any

import click

from ..copyright import SpdxExpression
from ..exceptions import GlobalLicensingConflictError, GlobalLicensingParseError
from ..i18n import _
from ..project import Project
from ..vcs import find_root


@dataclass()
class ClickObj:
    """A dataclass holding necessary context and options."""

    root: Path | None = None
    include_submodules: bool = False
    include_meson_subprojects: bool = False
    no_multiprocessing: bool = True

    @cached_property
    def project(self) -> Project:
        """Generate a project object on demand."""
        root = self.root
        if root is None:
            root = find_root()
        if root is None:
            root = Path.cwd()

        try:
            return Project.from_directory(
                root,
                include_submodules=self.include_submodules,
                include_meson_subprojects=self.include_meson_subprojects,
            )
        # FileNotFoundError and NotADirectoryError don't need to be caught
        # because argparse already made sure of these things.
        except GlobalLicensingParseError as error:
            raise click.UsageError(
                _(
                    "'{path}' could not be parsed. We received the"
                    " following error message: {message}"
                ).format(path=error.source, message=str(error))
            ) from error

        except (GlobalLicensingConflictError, OSError) as error:
            raise click.UsageError(str(error)) from error


class MutexOption(click.Option):
    """Enable declaring mutually exclusive options."""

    def __init__(self, *args: Any, **kwargs: Any):
        self.mutually_exclusive: set[str] = set(
            kwargs.pop("mutually_exclusive", [])
        )
        super().__init__(*args, **kwargs)
        # If self is in mutex, remove it.
        self.mutually_exclusive -= {self.name}

    @staticmethod
    def _get_long_name(ctx: click.Context, name: str) -> str:
        """Given the option name, get the long name of the option.

        For example, 'output' return '--output'.
        """
        param = next(
            param for param in ctx.command.params if param.name == name
        )
        return param.opts[0]

    def handle_parse_result(
        self, ctx: click.Context, opts: Mapping[str, Any], args: list[str]
    ) -> tuple[Any, list[str]]:
        if self.mutually_exclusive.intersection(opts) and self.name in opts:
            raise click.UsageError(
                _("'{name}' is mutually exclusive with: {opts}").format(
                    name=self._get_long_name(ctx, str(self.name)),
                    opts=", ".join(
                        f"'{self._get_long_name(ctx, opt)}'"
                        for opt in self.mutually_exclusive
                    ),
                )
            )
        return super().handle_parse_result(ctx, opts, args)


def spdx_identifier(text: str) -> SpdxExpression:
    """Factory for creating SPDX expressions."""
    expression = SpdxExpression(text)
    if not expression.is_valid:
        raise click.UsageError(
            _("'{}' is not a valid SPDX expression.").format(text)
        )
    return expression
