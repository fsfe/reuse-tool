# SPDX-FileCopyrightText: 2024 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Utilities that are common to multiple CLI commands."""

from dataclasses import dataclass
from typing import Any, Mapping, Optional

import click

from ..i18n import _
from ..project import Project


@dataclass(frozen=True)
class ClickObj:
    """A dataclass holding necessary context and options."""

    no_multiprocessing: bool
    project: Optional[Project]


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
            (param for param in ctx.command.params if param.name == name)
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
