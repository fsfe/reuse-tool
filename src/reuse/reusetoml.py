# SPDX-FileCopyrightText: 2023 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Code for parsing and validating REUSE.toml."""

import logging
from gettext import gettext as _
from typing import Any, Dict, List, Literal, Set, Type, cast

import attrs
import tomlkit
from boolean.boolean import Expression, ParseError
from license_expression import ExpressionError

from ._util import _LICENSING

_LOGGER = logging.getLogger(__name__)


def _validate_collection_of_type(
    instance: object,
    attribute: attrs.Attribute,
    value: List[Any],
    iterable_type: Type,
    type_: Type,
) -> None:
    # pylint: disable=unused-argument
    if not isinstance(value, iterable_type):
        msg = (
            f"'{attribute.name}' must be a {iterable_type.__name__} (got"
            f" {value!r} that is a {value.__class__!r})."
        )
        raise TypeError(msg, attribute, set, value)
    for item in value:
        if not isinstance(item, type_):
            msg = (
                f"Item in '{attribute.name}' collection must be a"
                f" {type_.__name__} (got {item!r} that is a {item.__class__!r})"
            )
            raise TypeError(msg, attribute, type_, item)


def _validate_set_of_str(
    instance: object, attribute: attrs.Attribute, value: List[Any]
) -> None:
    return _validate_collection_of_type(instance, attribute, value, set, str)


def _validate_set_of_expr(
    instance: object, attribute: attrs.Attribute, value: List[Any]
) -> None:
    return _validate_collection_of_type(
        instance, attribute, value, set, Expression
    )


def _validate_list_of_annotations_items(
    instance: object, attribute: attrs.Attribute, value: List[Any]
) -> None:
    return _validate_collection_of_type(
        instance, attribute, value, list, AnnotationsItem
    )


def _validate_literal(
    instance: object, attribute: attrs.Attribute, value: Any
) -> None:
    # pylint: disable=unused-argument
    if value not in cast(Type, attribute.type).__args__:
        raise ValueError(
            f"The value of '{attribute.name}' must be one of"
            " {attribute.type.__args__!r} (got {value!r})"
        )


def _str_to_set(value: Any) -> Set[Any]:
    if isinstance(value, str):
        return {value}
    if hasattr(value, "__iter__"):
        return set(value)
    return {value}


def _str_to_set_of_expr(value: Any) -> Set[Expression]:
    value = _str_to_set(value)
    result = set()
    for expression in value:
        try:
            result.add(_LICENSING.parse(expression))
        except (ExpressionError, ParseError):
            _LOGGER.error(
                _("Could not parse '{expression}'").format(
                    expression=expression
                )
            )
            raise
    return result


@attrs.define
class AnnotationsItem:
    """A class that maps to a single [[annotations]] table element in
    REUSE.toml.
    """

    paths: Set[str] = attrs.field(
        converter=_str_to_set, validator=_validate_set_of_str
    )
    precedence: Literal["aggregate", "file", "toml"] = attrs.field(
        validator=_validate_literal
    )
    copyright_lines: Set[str] = attrs.field(
        converter=_str_to_set, validator=_validate_set_of_str
    )
    spdx_expressions: Set[Expression] = attrs.field(
        converter=_str_to_set_of_expr, validator=_validate_set_of_expr
    )

    @classmethod
    def from_dict(cls, values: Dict[str, Any]) -> "AnnotationsItem":
        """Create an :class:`AnnotationsItem` from a dictionary that uses the
        key-value pairs for an [[annotations]] table in REUSE.toml.
        """
        new_dict = {}
        new_dict["paths"] = values.get("path")
        new_dict["precedence"] = values.get("precedence")
        new_dict["copyright_lines"] = values.get("SPDX-FileCopyrightText")
        new_dict["spdx_expressions"] = values.get("SPDX-License-Identifier")
        return cls(**new_dict)  # type: ignore


@attrs.define
class ReuseTOML:
    """A class that contains the data parsed from a REUSE.toml file.

    TODO: There are strict typing requirements about the key-value pairs.
    """

    version: int = attrs.field(validator=attrs.validators.instance_of(int))
    source: str = attrs.field(validator=attrs.validators.instance_of(str))
    annotations: List[AnnotationsItem] = attrs.field(
        validator=_validate_list_of_annotations_items
    )

    @classmethod
    def from_dict(cls, values: Dict[str, Any], source: str) -> "ReuseTOML":
        """Create a :class:`ReuseTOML` from the dict version of REUSE.toml."""
        new_dict = {}
        new_dict["version"] = values.get("version")
        new_dict["source"] = source

        annotation_dicts = values.get("annotations", [])
        annotations = [
            AnnotationsItem.from_dict(annotation)
            for annotation in annotation_dicts
        ]

        new_dict["annotations"] = annotations

        return cls(**new_dict)  # type: ignore

    @classmethod
    def from_toml(cls, toml: str, source: str) -> "ReuseTOML":
        """Create a :class:`ReuseTOML` from TOML text."""
        tomldict = tomlkit.loads(toml)
        return cls.from_dict(tomldict, source)
