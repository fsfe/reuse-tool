# SPDX-FileCopyrightText: 2023 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""REUSE configuration."""

from dataclasses import dataclass, field
from gettext import gettext as _
from os import PathLike
from pathlib import Path, PurePath
from typing import Any, Dict, Optional

import yaml


@dataclass
class AnnotateOptions:
    """An object to hold the default values for annotation."""

    name: Optional[str] = None
    contact: Optional[str] = None
    license: Optional[str] = None

    def merge(self, other: "AnnotateOptions") -> "AnnotateOptions":
        """Return a copy of *self*, but replace attributes with truthy
        attributes of *other*.
        """
        new_kwargs = {}
        for key, value in self.__dict__.items():
            if other_value := getattr(other, key):
                value = other_value
            new_kwargs[key] = value
        return self.__class__(**new_kwargs)


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

    @classmethod
    def from_yaml(cls, text: str) -> "Config":
        """Parse yaml to generate a Config object.

        An example of a yaml file::

            annotate:
              default_name: Jane Doe
              default_contact: jane@example.com
              default_license: GPL-3.0-or-later

              overrides:
                - path: ~/Projects/FSFE
                  default_contact: jane@fsfe.example.com
        """
        return cls.from_dict(yaml.load(text, Loader=yaml.Loader))

    # TODO: We could probably smartly cache the results somehow.
    def annotations_for_path(self, path: PathLike) -> AnnotateOptions:
        """TODO: Document the precise behaviour."""
        path = PurePath(path)
        result = self.global_annotate_options
        # This assumes that the override options are ordered by reverse
        # precedence.
        for o_path, options in self.override_annotate_options.items():
            o_path = Path(o_path).expanduser()
            if path.is_relative_to(o_path):
                result = result.merge(options)
        return result


def _annotate_options_from_dict(value: Dict[str, str]) -> AnnotateOptions:
    return AnnotateOptions(
        name=value.get("default_name"),
        contact=value.get("default_contact"),
        license=value.get("default_license"),
    )
