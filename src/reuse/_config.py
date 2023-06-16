# SPDX-FileCopyrightText: 2023 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""REUSE configuration."""

from dataclasses import dataclass, field
from gettext import gettext as _
from typing import Any, Dict, Optional


@dataclass
class AnnotateOptions:
    """An object to hold the default values for annotation."""

    name: Optional[str] = None
    contact: Optional[str] = None
    license: Optional[str] = None


@dataclass
class Config:
    """Object to hold all configuration options."""

    global_annotate_options: AnnotateOptions = field(
        default_factory=AnnotateOptions
    )
    #: Only truthy attributes override the global options. The key is the path
    #: to which the override options apply.
    override_annotate_options: Dict[str, AnnotateOptions] = field(
        default_factory=dict
    )

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "Config":
        """Factory method to create a Config from a dictionary."""
        config = cls()
        if annotate := value.get("annotate"):
            config.global_annotate_options = _annotate_options_from_dict(
                annotate
            )
            for override in annotate.get("overrides", []):
                if not (path := override.get("path")):
                    raise ValueError(
                        _("'path' key is missing from one of the overrides.")
                    )
                config.override_annotate_options[
                    path
                ] = _annotate_options_from_dict(override)
        return config


def _annotate_options_from_dict(value: Dict[str, str]) -> AnnotateOptions:
    return AnnotateOptions(
        name=value.get("default_name"),
        contact=value.get("default_contact"),
        license=value.get("default_license"),
    )
