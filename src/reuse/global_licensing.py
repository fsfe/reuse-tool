# SPDX-FileCopyrightText: 2023 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Code for parsing and validating REUSE.toml."""

# mypy: disable-error-code=attr-defined

import contextlib
import logging
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from enum import Enum
from gettext import gettext as _
from pathlib import Path, PurePath
from typing import (
    Any,
    Callable,
    Collection,
    Dict,
    Generator,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

import attrs
import tomlkit
from attr.validators import _InstanceOfValidator as _AttrInstanceOfValidator
from boolean.boolean import Expression, ParseError
from debian.copyright import Copyright
from debian.copyright import Error as DebianError
from license_expression import ExpressionError

from . import ReuseInfo, SourceType
from ._util import _LICENSING, StrPath

_LOGGER = logging.getLogger(__name__)

_T = TypeVar("_T")

#: Current version of REUSE.toml.
REUSE_TOML_VERSION = 1


class PrecedenceType(Enum):
    """An enum of behaviours surrounding order of precedence for entries in a
    :class:`GlobalLicensing`.
    """

    #: Aggregate the results from the file with the results from the global
    #: licensing file.
    AGGREGATE = "aggregate"
    #: Use the results that are closest to the covered file. This is typically
    #: the file itself, or the global licensing file if no REUSE information
    #: exists inside of the file.
    CLOSEST = "closest"
    #: Only use the results from the global licensing file.
    OVERRIDE = "override"


class GlobalLicensingParseError(Exception):
    """An exception representing any kind of error that occurs when trying to
    parse a :class:`GlobalLicensing` file.
    """


class GlobalLicensingParseTypeError(TypeError, GlobalLicensingParseError):
    """An exception representing a type error while trying to parse a
    :class:`GlobalLicensing` file.
    """


class GlobalLicensingParseValueError(GlobalLicensingParseError, ValueError):
    """An exception representing a value error while trying to parse a
    :class:`GlobalLicensing` file.
    """


@attrs.define
class _CollectionOfValidator:
    collection_type: Type[Collection] = attrs.field()
    value_type: Type = attrs.field()
    optional: bool = attrs.field(default=True)

    def __call__(
        self,
        instance: object,
        attribute: attrs.Attribute,
        value: Collection[_T],
    ) -> None:
        # This is a hack to display the TOML's key names instead of the Python
        # attributes.
        if hasattr(instance, "TOML_KEYS"):
            attr_name = instance.TOML_KEYS[attribute.name]
        else:
            attr_name = attribute.name

        if not isinstance(value, self.collection_type):
            raise GlobalLicensingParseTypeError(
                _(
                    "{attr_name} must be a {type_name} (got {value} that is a"
                    " {value_class})."
                ).format(
                    attr_name=repr(attr_name),
                    type_name=self.collection_type.__name__,
                    value=repr(value),
                    value_class=repr(value.__class__),
                )
            )
        for item in value:
            if not isinstance(item, self.value_type):
                raise GlobalLicensingParseTypeError(
                    _(
                        "Item in {attr_name} collection must be a {type_name}"
                        " (got {item_value} that is a {item_class})."
                    ).format(
                        attr_name=repr(attr_name),
                        type_name=self.value_type.__name__,
                        item_value=repr(item),
                        item_class=repr(item.__class__),
                    )
                )
        if not self.optional and not value:
            raise GlobalLicensingParseValueError(
                _("{attr_name} must not be empty.").format(
                    attr_name=repr(attr_name)
                )
            )


def _validate_collection_of(
    collection_type: Type[Collection],
    value_type: Type[_T],
    optional: bool = False,
) -> Callable[[Any, attrs.Attribute, Collection[_T]], Any]:
    return _CollectionOfValidator(
        collection_type, value_type, optional=optional
    )


class _InstanceOfValidator(_AttrInstanceOfValidator):
    def __call__(self, inst: Any, attr: attrs.Attribute, value: _T) -> None:
        try:
            super().__call__(inst, attr, value)
        except TypeError as error:
            raise GlobalLicensingParseTypeError(
                _(
                    "{name} must be a {type} (got {value} that is a"
                    " {value_type})."
                ).format(
                    name=repr(error.args[1].name),
                    type=repr(error.args[2].__name__),
                    value=repr(error.args[3]),
                    value_type=repr(error.args[3].__class__),
                )
            ) from error


def _instance_of(
    type_: Type[_T],
) -> Callable[[Any, attrs.Attribute, _T], Any]:
    return _InstanceOfValidator(type_)


def _str_to_global_precedence(value: Any) -> PrecedenceType:
    try:
        return PrecedenceType(value)
    except ValueError as err:
        raise GlobalLicensingParseValueError(
            _(
                "The value of 'precedence' must be one of {precedence_vals}"
                " (got {received})"
            ).format(
                precedence_vals=tuple(
                    member.value for member in PrecedenceType
                ),
                received=repr(value),
            )
        ) from err


@overload
def _str_to_set(value: str) -> Set[str]: ...


@overload
def _str_to_set(value: Union[None, _T, Collection[_T]]) -> Set[_T]: ...


def _str_to_set(
    value: Union[str, None, _T, Collection[_T]]
) -> Union[Set[str], Set[_T]]:
    if value is None:
        return cast(Set[str], set())
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
        except (ExpressionError, ParseError) as error:
            raise GlobalLicensingParseValueError(
                _("Could not parse '{expression}'").format(
                    expression=expression
                )
            ) from error
    return result


@attrs.define
class GlobalLicensing(ABC):
    """An abstract class that represents a configuration file that contains
    licensing information that is pertinent to other files in the project.
    """

    source: str = attrs.field(validator=_instance_of(str))

    @classmethod
    @abstractmethod
    def from_file(cls, path: StrPath) -> "GlobalLicensing":
        """Parse the file and create a :class:`GlobalLicensing` object from its
        contents.

        Raises:
            FileNotFoundError: file doesn't exist.
            UnicodeDecodeError: could not decode file as UTF-8.
            OSError: some other error surrounding I/O.
            GlobalLicensingParseError: file could not be parsed.
        """

    @abstractmethod
    def reuse_info_of(
        self, path: StrPath
    ) -> Dict[PrecedenceType, List[ReuseInfo]]:
        """Find the REUSE information of *path* defined in the configuration.
        The path must be relative to the root of a
        :class:`reuse.project.Project`.

        The key indicates the precedence type for the subsequent information.
        """


@attrs.define
class ReuseDep5(GlobalLicensing):
    """A soft wrapper around :class:`Copyright`."""

    dep5_copyright: Copyright

    @classmethod
    def from_file(cls, path: StrPath) -> "ReuseDep5":
        path = Path(path)
        try:
            with path.open(encoding="utf-8") as fp:
                return cls(str(path), Copyright(fp))
        except UnicodeDecodeError:
            raise
        # TODO: Remove ValueError once
        # <https://salsa.debian.org/python-debian-team/python-debian/-/merge_requests/123>
        # is closed
        except (DebianError, ValueError) as error:
            raise GlobalLicensingParseError(str(error)) from error

    def reuse_info_of(
        self, path: StrPath
    ) -> Dict[PrecedenceType, List[ReuseInfo]]:
        path = PurePath(path).as_posix()
        result = self.dep5_copyright.find_files_paragraph(path)

        if result is None:
            return {}

        return {
            PrecedenceType.AGGREGATE: [
                ReuseInfo(
                    spdx_expressions=set(
                        map(_LICENSING.parse, [result.license.synopsis])
                    ),
                    copyright_lines=set(
                        map(str.strip, result.copyright.splitlines())
                    ),
                    path=path,
                    source_type=SourceType.DEP5,
                    # This is hardcoded. It must be a relative path from the
                    # project root. self.source is not (guaranteed) a relative
                    # path.
                    source_path=".reuse/dep5",
                )
            ]
        }


@attrs.define
class AnnotationsItem:
    """A class that maps to a single [[annotations]] table element in
    REUSE.toml.
    """

    TOML_KEYS = {
        "paths": "path",
        "precedence": "precedence",
        "copyright_lines": "SPDX-FileCopyrightText",
        "spdx_expressions": "SPDX-License-Identifier",
    }

    paths: Set[str] = attrs.field(
        converter=_str_to_set,
        validator=_validate_collection_of(set, str, optional=False),
    )
    precedence: PrecedenceType = attrs.field(
        converter=_str_to_global_precedence, default=PrecedenceType.CLOSEST
    )
    copyright_lines: Set[str] = attrs.field(
        converter=_str_to_set,
        validator=_validate_collection_of(set, str, optional=True),
        default=None,
    )
    spdx_expressions: Set[Expression] = attrs.field(
        converter=_str_to_set_of_expr,
        validator=_validate_collection_of(set, Expression, optional=True),
        default=None,
    )

    _paths_regex: re.Pattern = attrs.field(init=False)

    def __attrs_post_init__(self) -> None:
        def translate(path: str) -> str:
            blocks = []
            escaping = False
            globstar = False
            prev_char = ""
            for char in path:
                if char == "\\":
                    if prev_char == "\\" and escaping:
                        escaping = False
                        blocks.append(r"\\")
                    else:
                        escaping = True
                elif char == "*":
                    if escaping:
                        blocks.append(re.escape("*"))
                        escaping = False
                    elif prev_char == "*" and not globstar:
                        globstar = True
                        blocks.append(r".*")
                elif char == "/":
                    if not globstar:
                        blocks.append("/")
                    escaping = False
                else:
                    if prev_char == "*" and not globstar:
                        blocks.append(r"[^/]*")
                    blocks.append(re.escape(char))
                    globstar = False
                    escaping = False
                prev_char = char
            if prev_char == "*" and not globstar:
                blocks.append(r"[^/]*")
            result = "".join(blocks)
            return f"^({result})$"

        self._paths_regex = re.compile(
            "|".join(translate(path) for path in self.paths)
        )

    @classmethod
    def from_dict(cls, values: Dict[str, Any]) -> "AnnotationsItem":
        """Create an :class:`AnnotationsItem` from a dictionary that uses the
        key-value pairs for an [[annotations]] table in REUSE.toml.
        """
        new_dict = {}
        new_dict["paths"] = values.get(cls.TOML_KEYS["paths"])
        precedence = values.get(cls.TOML_KEYS["precedence"])
        if precedence is not None:
            new_dict["precedence"] = precedence
        new_dict["copyright_lines"] = values.get(
            cls.TOML_KEYS["copyright_lines"]
        )
        new_dict["spdx_expressions"] = values.get(
            cls.TOML_KEYS["spdx_expressions"]
        )
        return cls(**new_dict)  # type: ignore

    def matches(self, path: str) -> bool:
        """Determine whether *path* matches any of the paths (or path globs) in
        :class:`AnnotationsItem`.
        """
        return bool(self._paths_regex.match(path))


@attrs.define
class ReuseTOML(GlobalLicensing):
    """A class that contains the data parsed from a REUSE.toml file."""

    version: int = attrs.field(validator=_instance_of(int))
    annotations: List[AnnotationsItem] = attrs.field(
        validator=_validate_collection_of(list, AnnotationsItem, optional=True)
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
        try:
            tomldict = tomlkit.loads(toml)
        except tomlkit.exceptions.TOMLKitError as error:
            raise GlobalLicensingParseError(str(error)) from error
        return cls.from_dict(tomldict, source)

    @classmethod
    def from_file(cls, path: StrPath) -> "ReuseTOML":
        with Path(path).open(encoding="utf-8") as fp:
            return cls.from_toml(fp.read(), str(path))

    def find_annotations_item(self, path: StrPath) -> Optional[AnnotationsItem]:
        """Find a :class:`AnnotationsItem` that matches *path*. The latest match
        in :attr:`annotations` is returned.
        """
        path = PurePath(path).as_posix()
        for item in reversed(self.annotations):
            if item.matches(path):
                return item
        return None

    def reuse_info_of(
        self, path: StrPath
    ) -> Dict[PrecedenceType, List[ReuseInfo]]:
        path = PurePath(path).as_posix()
        item = self.find_annotations_item(path)
        if item:
            return {
                item.precedence: [
                    ReuseInfo(
                        spdx_expressions=item.spdx_expressions,
                        copyright_lines=item.copyright_lines,
                        path=path,
                        source_path="REUSE.toml",
                        source_type=SourceType.REUSE_TOML,
                    )
                ]
            }
        return {}

    @property
    def directory(self) -> PurePath:
        """The directory in which the REUSE.toml file is located."""
        return PurePath(self.source).parent


@attrs.define
class NestedReuseTOML(GlobalLicensing):
    """A class that represents a hierarchy of :class:`ReuseTOML` objects."""

    reuse_tomls: List[ReuseTOML] = attrs.field()

    @classmethod
    def from_file(cls, path: StrPath) -> "GlobalLicensing":
        """TODO: *path* is a directory instead of a file."""
        tomls = [
            ReuseTOML.from_file(toml_path)
            for toml_path in cls.find_reuse_tomls(path)
        ]
        return cls(reuse_tomls=tomls, source=str(path))

    def reuse_info_of(
        self, path: StrPath
    ) -> Dict[PrecedenceType, List[ReuseInfo]]:
        path = PurePath(path)

        toml_items: List[Tuple[ReuseTOML, AnnotationsItem]] = (
            self._find_relevant_tomls_and_items(path)
        )

        result = defaultdict(list)
        for keyval in toml_items:
            toml = keyval[0]
            item = keyval[1]
            relpath = (PurePath(self.source) / path).relative_to(toml.directory)
            # I'm pretty sure there should be no KeyError here.
            info = toml.reuse_info_of(relpath)[item.precedence][0]
            result[item.precedence].append(
                # Fix the paths to be relative to self.source. As-is, they
                # were relative to the directory of the respective
                # REUSE.toml.
                info.copy(
                    path=path.as_posix(),
                    source_path=PurePath(toml.source)
                    .relative_to(self.source)
                    .as_posix(),
                )
            )
            if item.precedence == PrecedenceType.OVERRIDE:
                # No more!
                break

        # Clean up CLOSEST. Some items were added that are not the closest.
        # Consider copyright and licensing separately.
        copyright_found = False
        licence_found = False
        to_keep: List[ReuseInfo] = []
        for info in reversed(result[PrecedenceType.CLOSEST]):
            new_info = info.copy(copyright_lines=set(), spdx_expressions=set())
            if not copyright_found and info.copyright_lines:
                new_info = new_info.copy(copyright_lines=info.copyright_lines)
                copyright_found = True
            if not licence_found and info.spdx_expressions:
                new_info = new_info.copy(spdx_expressions=info.spdx_expressions)
                licence_found = True
            if new_info.contains_copyright_or_licensing():
                to_keep.append(new_info)
        result[PrecedenceType.CLOSEST] = list(reversed(to_keep))
        # Looping over CLOSEST created it in the defaultdict. Remove it if it's
        # empty.
        if not result[PrecedenceType.CLOSEST]:
            del result[PrecedenceType.CLOSEST]

        return dict(result)

    @classmethod
    def find_reuse_tomls(cls, path: StrPath) -> Generator[Path, None, None]:
        """Find all REUSE.toml files in *path*."""
        return Path(path).rglob("**/REUSE.toml")

    def _find_relevant_tomls(self, path: StrPath) -> List[ReuseTOML]:
        found = []
        for toml in self.reuse_tomls:
            # TODO: When Python 3.8 is dropped, use is_relative_to instead.
            with contextlib.suppress(ValueError):
                PurePath(path).relative_to(toml.directory)
                # No error.
                found.append(toml)
        # Sort from topmost to deepest directory.
        found.sort(key=lambda toml: toml.directory.parts)
        return found

    def _find_relevant_tomls_and_items(
        self, path: StrPath
    ) -> List[Tuple[ReuseTOML, AnnotationsItem]]:
        # *path* is relative to the Project root, which is the *source* of
        # NestedReuseTOML, which itself is a relative (to CWD) or absolute
        # path.
        path = PurePath(path)
        adjusted_path = PurePath(self.source) / path

        tomls = self._find_relevant_tomls(adjusted_path)
        toml_items: List[Tuple[ReuseTOML, AnnotationsItem]] = []
        for toml in tomls:
            relpath = adjusted_path.relative_to(toml.directory)
            item = toml.find_annotations_item(relpath)
            if item is not None:
                toml_items.append((toml, item))
        return toml_items
