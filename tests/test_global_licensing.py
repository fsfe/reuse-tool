# SPDX-FileCopyrightText: 2023 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for REUSE.toml and .reuse/dep5."""

import shutil
from inspect import cleandoc
from pathlib import Path

import pytest
from conftest import RESOURCES_DIRECTORY, posix
from debian.copyright import Copyright
from license_expression import LicenseSymbol

from reuse import ReuseInfo, SourceType
from reuse._util import _LICENSING
from reuse.global_licensing import (
    AnnotationsItem,
    GlobalLicensingParseError,
    GlobalLicensingParseTypeError,
    GlobalLicensingParseValueError,
    NestedReuseTOML,
    PrecedenceType,
    ReuseDep5,
    ReuseTOML,
)

# REUSE-IgnoreStart

# pylint: disable=redefined-outer-name,too-many-lines


@pytest.fixture()
def annotations_item():
    return AnnotationsItem({"foo.py"}, "override", {"2023 Jane Doe"}, {"MIT"})


class TestAnnotationsItemValidators:
    """Test the validators of AnnotationsItem."""

    def test_simple(self):
        """Create an AnnotationsItem, passing all validators."""
        item = AnnotationsItem(
            {"foo.py"},
            "override",
            {"2023 Jane Doe"},
            {"MIT"},
        )
        assert item.paths == {"foo.py"}
        assert item.precedence == PrecedenceType.OVERRIDE
        assert item.copyright_lines == {"2023 Jane Doe"}
        assert item.spdx_expressions == {_LICENSING.parse("MIT")}

    def test_precedence_defaults_to_closest(self):
        """If precedence is NOTHING, default to closest."""
        item = AnnotationsItem(
            {"foo.py"},
            copyright_lines={"2023 Jane Doe"},
            spdx_expressions={"MIT"},
        )
        assert item.precedence == PrecedenceType.CLOSEST

    def test_from_list(self):
        """Convert lists to sets."""
        item = AnnotationsItem(
            ["foo.py"],
            "override",
            ["2023 Jane Doe"],
            ["MIT"],
        )
        assert item.paths == {"foo.py"}
        assert item.precedence == PrecedenceType.OVERRIDE
        assert item.copyright_lines == {"2023 Jane Doe"}
        assert item.spdx_expressions == {_LICENSING.parse("MIT")}

    def test_str_to_set(self):
        """Convert strings to sets."""
        item = AnnotationsItem(
            "foo.py",
            "override",
            "2023 Jane Doe",
            "MIT",
        )
        assert item.paths == {"foo.py"}
        assert item.precedence == PrecedenceType.OVERRIDE
        assert item.copyright_lines == {"2023 Jane Doe"}
        assert item.spdx_expressions == {_LICENSING.parse("MIT")}

    def test_bad_expr(self):
        """Raise an error on malformed SPDX expressions."""
        with pytest.raises(GlobalLicensingParseError):
            AnnotationsItem(
                {"foo.py"},
                {"MIT OR"},
            )

    def test_bad_literal(self):
        """Only a limited set of literal are accepted for precedence."""
        with pytest.raises(GlobalLicensingParseValueError):
            AnnotationsItem(
                {"foo.py"},
                "foobar",
            )

    def test_not_str(self):
        """Copyright must be a string."""
        with pytest.raises(GlobalLicensingParseTypeError):
            AnnotationsItem(
                {"foo.py"},
                copyright_lines=123,
            )

    def test_not_set_of_str(self):
        """Copyright must be a set of strings."""
        with pytest.raises(GlobalLicensingParseTypeError):
            AnnotationsItem(
                {"foo.py"},
                copyright_lines={"2023 Jane Doe", 2024},
            )

    def test_paths_must_not_be_empty(self):
        """'paths' may not be an empty list."""
        with pytest.raises(GlobalLicensingParseValueError):
            AnnotationsItem(
                set(),
            )

    def test_everything_except_path_optional(self):
        """All fields except path are optional."""
        AnnotationsItem({"foo.py"})


class TestAnnotationsItemFromDict:
    """Test AnnotationsItem's from_dict method."""

    def test_simple(self):
        """A simple case."""
        item = AnnotationsItem.from_dict(
            {
                "path": {"foo.py"},
                "precedence": "override",
                "SPDX-FileCopyrightText": {"2023 Jane Doe"},
                "SPDX-License-Identifier": {"MIT"},
            }
        )
        assert item.paths == {"foo.py"}
        assert item.precedence == PrecedenceType.OVERRIDE
        assert item.copyright_lines == {"2023 Jane Doe"}
        assert item.spdx_expressions == {_LICENSING.parse("MIT")}

    def test_implicit_precedence(self):
        """When precedence is not defined, default to closest."""
        item = AnnotationsItem.from_dict(
            {
                "path": {"foo.py"},
            }
        )
        assert item.precedence == PrecedenceType.CLOSEST

    def test_trigger_validators(self):
        """It's possible to trigger the validators by providing a bad value."""
        with pytest.raises(GlobalLicensingParseTypeError):
            AnnotationsItem.from_dict(
                {
                    "path": {123},
                }
            )

    def test_path_missing(self):
        """If the path key is missing, raise an error."""
        with pytest.raises(GlobalLicensingParseValueError):
            AnnotationsItem.from_dict(
                {
                    "precedence": "override",
                    "SPDX-FileCopyrightText": {"2023 Jane Doe"},
                    "SPDX-License-Identifier": {"MIT"},
                }
            )

    def test_path_none(self):
        """If the path key is None, raise an error."""
        with pytest.raises(GlobalLicensingParseValueError):
            AnnotationsItem.from_dict(
                {
                    "path": None,
                }
            )

    def test_one_key_missing(self):
        """If one REUSE info key is missing, raise no error."""
        item = AnnotationsItem.from_dict(
            {
                "path": {"foo.py"},
                "SPDX-License-Identifier": {"MIT"},
            }
        )
        assert not item.copyright_lines
        assert isinstance(item.copyright_lines, set)

    def test_both_keys_missing(self):
        """If both REUSE info keys are missing, raise no error."""
        item = AnnotationsItem.from_dict(
            {
                "path": {"foo.py"},
            }
        )
        assert not item.copyright_lines
        assert not item.spdx_expressions


class TestAnnotationsItemMatches:
    """Test AnnotationsItem's matches method."""

    def test_simple(self):
        """Simple case."""
        item = AnnotationsItem(paths=["foo.py"])
        assert item.matches("foo.py")
        assert not item.matches("src/foo.py")
        assert not item.matches("bar.py")

    def test_in_directory(self):
        """Correctly handle pathname separators. Looking at you, Windows."""
        item = AnnotationsItem(paths=["src/foo.py"])
        assert item.matches("src/foo.py")
        assert not item.matches("foo.py")

    def test_all_py(self):
        """Correctly find all Python files."""
        item = AnnotationsItem(paths=["**/*.py"])
        assert item.matches("foo.py")
        assert item.matches(".foo.py")
        assert item.matches("src/foo.py")
        assert not item.matches("src/foo.js")

    def test_only_in_dir(self):
        """Only find files in a certain directory."""
        item = AnnotationsItem(paths=["src/*.py"])
        assert not item.matches("foo.py")
        assert item.matches("src/foo.py")
        assert not item.matches("src/other/foo.py")

    def test_asterisk(self):
        """Match everything in local directory."""
        item = AnnotationsItem(paths=["*"])
        assert item.matches("foo.py")
        assert item.matches(".gitignore")
        assert not item.matches("src/foo.py")
        assert not item.matches(".foo/bar")

    def test_asterisk_asterisk(self):
        """Match everything."""
        item = AnnotationsItem(paths=["**"])
        assert item.matches("foo.py")
        assert item.matches(".gitignore")
        assert item.matches("src/foo.py")
        assert item.matches(".foo/bar")

    def test_escape_asterisk(self):
        """Handle escape asterisk."""
        item = AnnotationsItem(paths=[r"\*.py"])
        assert item.matches("*.py")
        assert not item.matches("foo.py")

    def test_escape_asterisk_asterisk(self):
        """Handle escape asterisk asterisk."""
        item = AnnotationsItem(paths=[r"\**.py"])
        assert item.matches("*foo.py")
        assert not item.matches("foo.py")

    def test_escape_asterisk_escape_asterisk(self):
        """Handle escape asterisk escape asterisk."""
        item = AnnotationsItem(paths=[r"\*\*.py"])
        assert item.matches("**.py")
        assert not item.matches("foo.py")
        assert not item.matches("*foo.py")

    def test_escape_asterisk_asterisk_slash_asterisk(self):
        """Handle escape asterisk asterisk slash asterisk."""
        item = AnnotationsItem(paths=[r"\**/*.py"])
        assert item.matches("*foo/foo.py")
        assert not item.matches("bar/foo.py")

    def test_escape_asterisk_escape_asterisk_slash_asterisk(self):
        """Handle escape asterisk escape asterisk slash asterisk."""
        item = AnnotationsItem(paths=[r"\*\*/*.py"])
        assert item.matches("**/foo.py")
        assert not item.matches("bar/foo.py")
        assert not item.matches("*foo/foo.py")

    def test_escape_escape_asterisk(self):
        """Handle escape escape asterisk."""
        item = AnnotationsItem(paths=[r"\\*.py"])
        assert item.matches(r"\foo.py")

    def test_asterisk_asterisk_asterisk(self):
        """Handle asterisk asterisk asterisk."""
        item = AnnotationsItem(paths=[r"***.py"])
        assert item.matches("foo/bar/quz.py")

    def test_escape_a(self):
        """Handle escape a."""
        item = AnnotationsItem(paths=[r"\a"])
        assert item.matches(r"a")
        assert not item.matches(r"\a")

    def test_middle_asterisk(self):
        """See what happens if the asterisk is in the middle of the path."""
        item = AnnotationsItem(paths=["foo*bar"])
        assert item.matches("foobar")
        assert item.matches("foo2bar")
        assert not item.matches("foo")
        assert not item.matches("bar")
        assert not item.matches("foo/bar")

    def test_multiple_paths(self):
        """Match one of multiple files."""
        item = AnnotationsItem(paths=["*.py", "*.js", "README"])
        assert item.matches("foo.py")
        assert item.matches(".foo.py")
        assert item.matches("foo.js")
        assert item.matches("README")
        assert item.matches("README.py")
        assert not item.matches("README.md")

    def test_match_all(self):
        """Match everything."""
        item = AnnotationsItem(paths=["**"])
        assert item.matches("foo.py")
        assert item.matches("src/foo.py")
        assert item.matches(".gitignore")
        assert item.matches(".foo/bar")


class TestReuseTOMLValidators:
    """Test the validators of ReuseTOML."""

    def test_simple(self, annotations_item):
        """Pass the validators"""
        result = ReuseTOML(
            version=1, source="REUSE.toml", annotations=[annotations_item]
        )
        assert result.version == 1
        assert result.source == "REUSE.toml"
        assert result.annotations[0] == annotations_item

    def test_version_not_int(self, annotations_item):
        """Version must be an int"""
        with pytest.raises(GlobalLicensingParseTypeError):
            ReuseTOML(
                version=1.2, source="REUSE.toml", annotations=[annotations_item]
            )

    def test_source_not_str(self, annotations_item):
        """Source must be a str."""
        with pytest.raises(GlobalLicensingParseTypeError):
            ReuseTOML(version=1, source=123, annotations=[annotations_item])

    def test_annotations_must_be_list(self, annotations_item):
        """Annotations must be in a list, not any other collection."""
        # TODO: Technically we could change this to 'any collection that is
        # ordered', but let's not split hairs.
        with pytest.raises(GlobalLicensingParseTypeError):
            ReuseTOML(
                version=1,
                source="REUSE.toml",
                annotations=iter([annotations_item]),
            )

    def test_annotations_must_be_object(self):
        """Annotations must be AnnotationsItem objects."""
        with pytest.raises(GlobalLicensingParseTypeError):
            ReuseTOML(
                version=1, source="REUSE.toml", annotations=[{"foo": "bar"}]
            )


class TestReuseTOMLFromDict:
    """Test the from_dict method of ReuseTOML."""

    def test_simple(self, annotations_item):
        """Simple case."""
        result = ReuseTOML.from_dict(
            {
                "version": 1,
                "annotations": [
                    {
                        "path": {"foo.py"},
                        "precedence": "override",
                        "SPDX-FileCopyrightText": {"2023 Jane Doe"},
                        "SPDX-License-Identifier": {"MIT"},
                    }
                ],
            },
            "REUSE.toml",
        )
        assert result.version == 1
        assert result.source == "REUSE.toml"
        assert result.annotations[0] == annotations_item

    def test_no_annotations(self):
        """It's OK to not provide annotations."""
        result = ReuseTOML.from_dict({"version": 1}, source="REUSE.toml")
        assert result.annotations == []

    def test_annotations_empty_list(self):
        """It's OK if annotations is an empty list."""
        result = ReuseTOML.from_dict(
            {"version": 1, "annotations": []}, source="REUSE.toml"
        )
        assert result.annotations == []

    def test_no_version(self):
        """If the version is missing, raise an error."""
        with pytest.raises(GlobalLicensingParseTypeError):
            ReuseTOML.from_dict(
                {
                    "annotations": [
                        {
                            "path": {"foo.py"},
                            "precedence": "override",
                            "SPDX-FileCopyrightText": {"2023 Jane Doe"},
                            "SPDX-License-Identifier": {"MIT"},
                        }
                    ],
                },
                "REUSE.toml",
            )


class TestReuseTOMLFromToml:
    """Test the from_toml method of ReuseTOML."""

    def test_simple(self, annotations_item):
        """Simple case"""
        text = cleandoc(
            """
            version = 1

            [[annotations]]
            path = "foo.py"
            precedence = "override"
            SPDX-FileCopyrightText = "2023 Jane Doe"
            SPDX-License-Identifier = "MIT"
            """
        )
        result = ReuseTOML.from_toml(text, "REUSE.toml")
        assert result.version == 1
        assert result.source == "REUSE.toml"
        assert result.annotations[0] == annotations_item

    def test_syntax_error(self):
        """If there is a TOML syntax error, raise a GlobalLicensingParseError"""
        with pytest.raises(GlobalLicensingParseError):
            ReuseTOML.from_toml("version = 1,", "REUSE.toml")


class TestReuseTOMLEscaping:
    """Test the escaping functionality in paths in conjunction with reading from
    TOML.
    """

    def test_escape_asterisk(self):
        """Handle escape asterisk."""
        text = cleandoc(
            r"""
            version = 1

            [[annotations]]
            path = "\\*.py"
            SPDX-FileCopyrightText = "2023 Jane Doe"
            SPDX-License-Identifier = "MIT"
            """
        )
        toml = ReuseTOML.from_toml(text, "REUSE.toml")
        assert toml.reuse_info_of(r"*.py")
        assert not toml.reuse_info_of(r"\*.py")
        assert not toml.reuse_info_of(r"foo.py")
        assert not toml.reuse_info_of(r"\foo.py")

    @posix
    def test_escape_escape(self):
        """Handle escape escape."""
        text = cleandoc(
            r"""
            version = 1

            [[annotations]]
            path = "\\\\.py"
            SPDX-FileCopyrightText = "2023 Jane Doe"
            SPDX-License-Identifier = "MIT"
            """
        )
        toml = ReuseTOML.from_toml(text, "REUSE.toml")
        assert toml.reuse_info_of(r"\.py")


class TestReuseTOMLReuseInfoOf:
    """Test the reuse_info_of method of ReuseTOML."""

    def test_simple(self, annotations_item):
        """Simple test."""
        reuse_toml = ReuseTOML("REUSE.toml", 1, [annotations_item])
        assert reuse_toml.reuse_info_of("foo.py") == {
            PrecedenceType.OVERRIDE: [
                ReuseInfo(
                    spdx_expressions={_LICENSING.parse("MIT")},
                    copyright_lines={"2023 Jane Doe"},
                    path="foo.py",
                    source_path="REUSE.toml",
                    source_type=SourceType.REUSE_TOML,
                )
            ]
        }

    def test_latest_annotations_item(self, annotations_item):
        """If two items match, use exclusively the latest."""
        reuse_toml = ReuseTOML(
            "REUSE.toml",
            1,
            [
                annotations_item,
                AnnotationsItem(
                    paths={"foo.py"},
                    precedence="override",
                    copyright_lines={"2023 John Doe"},
                    spdx_expressions={"0BSD"},
                ),
            ],
        )
        assert reuse_toml.reuse_info_of("foo.py") == {
            PrecedenceType.OVERRIDE: [
                ReuseInfo(
                    spdx_expressions={_LICENSING.parse("0BSD")},
                    copyright_lines={"2023 John Doe"},
                    path="foo.py",
                    source_path="REUSE.toml",
                    source_type=SourceType.REUSE_TOML,
                )
            ]
        }

    def test_glob_all(self):
        """When globbing all, match everything."""
        reuse_toml = ReuseTOML(
            "REUSE.toml",
            1,
            [
                AnnotationsItem(
                    paths={"**"},
                    precedence="override",
                    copyright_lines={"2023 Jane Doe"},
                    spdx_expressions={"MIT"},
                ),
            ],
        )
        # Expected sans path
        expected = ReuseInfo(
            spdx_expressions={_LICENSING.parse("MIT")},
            copyright_lines={"2023 Jane Doe"},
            source_path="REUSE.toml",
            source_type=SourceType.REUSE_TOML,
        )
        assert reuse_toml.reuse_info_of("foo.py") == {
            PrecedenceType.OVERRIDE: [expected.copy(path="foo.py")]
        }
        assert reuse_toml.reuse_info_of("bar.py") == {
            PrecedenceType.OVERRIDE: [expected.copy(path="bar.py")]
        }
        assert reuse_toml.reuse_info_of("dir/subdir/foo.py") == {
            PrecedenceType.OVERRIDE: [expected.copy(path="dir/subdir/foo.py")]
        }

    def test_glob_py(self):
        """When globbing Python paths, match only .py files."""
        reuse_toml = ReuseTOML(
            "REUSE.toml",
            1,
            [
                AnnotationsItem(
                    paths={"**/*.py"},
                    precedence="override",
                    copyright_lines={"2023 Jane Doe"},
                    spdx_expressions={"MIT"},
                ),
            ],
        )
        assert reuse_toml.reuse_info_of("dir/foo.py") == {
            PrecedenceType.OVERRIDE: [
                ReuseInfo(
                    spdx_expressions={_LICENSING.parse("MIT")},
                    copyright_lines={"2023 Jane Doe"},
                    path="dir/foo.py",
                    source_path="REUSE.toml",
                    source_type=SourceType.REUSE_TOML,
                )
            ]
        }
        assert not reuse_toml.reuse_info_of("foo.c")


class TestReuseTOMLFromFile:
    """Test the from-file method of ReuseTOML."""

    def test_simple(self, annotations_item, empty_directory):
        """Simple case."""
        (empty_directory / "REUSE.toml").write_text(
            cleandoc(
                """
                version = 1

                [[annotations]]
                path = "foo.py"
                precedence = "override"
                SPDX-FileCopyrightText = "2023 Jane Doe"
                SPDX-License-Identifier = "MIT"
                """
            )
        )
        result = ReuseTOML.from_file("REUSE.toml")
        assert result.version == 1
        assert result.source == "REUSE.toml"
        assert result.annotations[0] == annotations_item

    def test_precedence_implicit(self, empty_directory):
        """When precedence is not set, default to closest."""
        (empty_directory / "REUSE.toml").write_text(
            cleandoc(
                """
                version = 1

                [[annotations]]
                path = "foo.py"
                SPDX-FileCopyrightText = "2023 Jane Doe"
                SPDX-License-Identifier = "MIT"
                """
            )
        )
        result = ReuseTOML.from_file("REUSE.toml")
        assert result.annotations[0].precedence == PrecedenceType.CLOSEST


class TestReuseTOMLDirectory:
    """Test the directory property of ReuseTOML."""

    def test_no_parent(self):
        """Test what happens if the source has no obvious parent."""
        toml = ReuseTOML(source="REUSE.toml", version=1, annotations=[])
        assert toml.directory == Path(".")

    def test_nested(self):
        """Correctly identify the directory of a nested file."""
        toml = ReuseTOML(source="src/REUSE.toml", version=1, annotations=[])
        assert toml.directory == Path("src")


class TestNestedReuseTOMLFromFile:
    """Tests for NestedReuseTOML.from_file."""

    def test_simple(self, fake_repository_reuse_toml):
        """Find a single REUSE.toml."""
        result = NestedReuseTOML.from_file(fake_repository_reuse_toml)
        path = fake_repository_reuse_toml / "REUSE.toml"
        assert result.reuse_tomls == [ReuseTOML.from_file(path)]

    def test_one_deep(self, empty_directory):
        """Find a single REUSE.toml deeper in the directory tree."""
        (empty_directory / "src").mkdir()
        path = empty_directory / "src/REUSE.toml"
        path.write_text("version = 1")
        result = NestedReuseTOML.from_file(empty_directory)
        assert result.reuse_tomls == [ReuseTOML.from_file(path)]

    def test_multiple(self, fake_repository_reuse_toml):
        """Find multiple REUSE.tomls."""
        (fake_repository_reuse_toml / "src/REUSE.toml").write_text(
            "version = 1"
        )
        result = NestedReuseTOML.from_file(fake_repository_reuse_toml)
        assert len(result.reuse_tomls) == 2
        assert (
            ReuseTOML.from_file(fake_repository_reuse_toml / "src/REUSE.toml")
        ) in result.reuse_tomls
        assert (
            ReuseTOML.from_file(fake_repository_reuse_toml / "REUSE.toml")
            in result.reuse_tomls
        )


class TestNestedReuseTOMLFindReuseTomls:
    """Tests for NestedReuseTOML.find_reuse_tomls."""

    def test_simple(self, fake_repository_reuse_toml):
        """Find a single REUSE.toml."""
        result = NestedReuseTOML.find_reuse_tomls(fake_repository_reuse_toml)
        assert list(result) == [fake_repository_reuse_toml / "REUSE.toml"]

    def test_one_deep(self, empty_directory):
        """Find a single REUSE.toml deeper in the directory tree."""
        (empty_directory / "src").mkdir()
        path = empty_directory / "src/REUSE.toml"
        path.touch()
        result = NestedReuseTOML.find_reuse_tomls(empty_directory)
        assert list(result) == [path]

    def test_multiple(self, fake_repository_reuse_toml):
        """Find multiple REUSE.tomls."""
        (fake_repository_reuse_toml / "src/REUSE.toml").touch()
        result = NestedReuseTOML.find_reuse_tomls(fake_repository_reuse_toml)
        assert set(result) == {
            fake_repository_reuse_toml / "REUSE.toml",
            fake_repository_reuse_toml / "src/REUSE.toml",
        }


class TestNestedReuseTOMLReuseInfoOf:
    """Tests for NestedReuseTOML.reuse_info_of."""

    def test_simple(self, annotations_item):
        """Simple case."""
        reuse_toml = ReuseTOML("REUSE.toml", 1, [annotations_item])
        nested_reuse_toml = NestedReuseTOML(".", [reuse_toml])
        assert nested_reuse_toml.reuse_info_of("foo.py") == {
            PrecedenceType.OVERRIDE: [
                ReuseInfo(
                    spdx_expressions={_LICENSING.parse("MIT")},
                    copyright_lines={"2023 Jane Doe"},
                    path="foo.py",
                    source_path="REUSE.toml",
                    source_type=SourceType.REUSE_TOML,
                )
            ]
        }
        assert not nested_reuse_toml.reuse_info_of("bar.py")

    def test_no_tomls(self):
        """Don't break when there are no nested ReuseTOMLs."""
        nested_reuse_toml = NestedReuseTOML(".", [])
        assert not nested_reuse_toml.reuse_info_of("foo.py")

    def test_skip_outer_closest(self):
        """If a precedence is set to 'closest', it is ignored unless it is the
        deepest element.
        """
        outer = ReuseTOML(
            "REUSE.toml",
            1,
            [
                AnnotationsItem(
                    "src/**",
                    precedence=PrecedenceType.CLOSEST,
                    copyright_lines={"Copyright Jane Doe"},
                    spdx_expressions={"MIT"},
                )
            ],
        )
        inner = ReuseTOML(
            "src/REUSE.toml",
            1,
            [
                AnnotationsItem(
                    "foo.py",
                    precedence=PrecedenceType.CLOSEST,
                    copyright_lines={"Copyright Alice"},
                    spdx_expressions={"0BSD"},
                )
            ],
        )
        toml = NestedReuseTOML(".", [outer, inner])
        assert toml.reuse_info_of("src/foo.py") == {
            PrecedenceType.CLOSEST: [
                ReuseInfo(
                    spdx_expressions={_LICENSING.parse("0BSD")},
                    copyright_lines={"Copyright Alice"},
                    path="src/foo.py",
                    source_path="src/REUSE.toml",
                    source_type=SourceType.REUSE_TOML,
                )
            ]
        }
        assert toml.reuse_info_of("src/bar.py") == {
            PrecedenceType.CLOSEST: [
                ReuseInfo(
                    spdx_expressions={_LICENSING.parse("MIT")},
                    copyright_lines={"Copyright Jane Doe"},
                    path="src/bar.py",
                    source_path="REUSE.toml",
                    source_type=SourceType.REUSE_TOML,
                )
            ]
        }

    def test_aggregate(self):
        """If a precedence is set to aggregate, aggregate."""
        outer = ReuseTOML(
            "REUSE.toml",
            1,
            [
                AnnotationsItem(
                    "src/**",
                    precedence=PrecedenceType.AGGREGATE,
                    copyright_lines={"Copyright Jane Doe"},
                    spdx_expressions={"MIT"},
                )
            ],
        )
        inner = ReuseTOML(
            "src/REUSE.toml",
            1,
            [
                AnnotationsItem(
                    "foo.py",
                    precedence=PrecedenceType.CLOSEST,
                    copyright_lines={"Copyright Alice"},
                    spdx_expressions={"0BSD"},
                )
            ],
        )
        toml = NestedReuseTOML(".", [outer, inner])
        assert toml.reuse_info_of("src/foo.py") == {
            PrecedenceType.AGGREGATE: [
                ReuseInfo(
                    spdx_expressions={_LICENSING.parse("MIT")},
                    copyright_lines={"Copyright Jane Doe"},
                    path="src/foo.py",
                    source_path="REUSE.toml",
                    source_type=SourceType.REUSE_TOML,
                )
            ],
            PrecedenceType.CLOSEST: [
                ReuseInfo(
                    spdx_expressions={_LICENSING.parse("0BSD")},
                    copyright_lines={"Copyright Alice"},
                    path="src/foo.py",
                    source_path="src/REUSE.toml",
                    source_type=SourceType.REUSE_TOML,
                ),
            ],
        }

    def test_toml_precedence(self):
        """If a precedence is set to toml, ignore deeper TOMLs."""
        outer = ReuseTOML(
            "REUSE.toml",
            1,
            [
                AnnotationsItem(
                    "src/**",
                    precedence=PrecedenceType.OVERRIDE,
                    copyright_lines={"Copyright Jane Doe"},
                    spdx_expressions={"MIT"},
                )
            ],
        )
        inner = ReuseTOML(
            "src/REUSE.toml",
            1,
            [
                AnnotationsItem(
                    "foo.py",
                    precedence=PrecedenceType.CLOSEST,
                    copyright_lines={"Copyright Alice"},
                    spdx_expressions={"0BSD"},
                )
            ],
        )
        toml = NestedReuseTOML(".", [outer, inner])
        assert toml.reuse_info_of("src/foo.py") == {
            PrecedenceType.OVERRIDE: [
                ReuseInfo(
                    spdx_expressions={_LICENSING.parse("MIT")},
                    copyright_lines={"Copyright Jane Doe"},
                    path="src/foo.py",
                    source_path="REUSE.toml",
                    source_type=SourceType.REUSE_TOML,
                ),
            ]
        }

    def test_toml_and_aggregate(self):
        """If the top TOML says aggregate and a deeper TOML has precedence toml,
        aggregate accordingly.
        """
        outer = ReuseTOML(
            "REUSE.toml",
            1,
            [
                AnnotationsItem(
                    "foo/bar/**",
                    precedence=PrecedenceType.AGGREGATE,
                    copyright_lines={"Copyright Jane Doe"},
                    spdx_expressions={"MIT"},
                )
            ],
        )
        mid = ReuseTOML(
            "foo/REUSE.toml",
            1,
            [
                AnnotationsItem(
                    "bar/**",
                    precedence=PrecedenceType.OVERRIDE,
                    copyright_lines={"Copyright Alice"},
                    spdx_expressions={"0BSD"},
                )
            ],
        )
        inner = ReuseTOML(
            "foo/bar/REUSE.toml",
            1,
            [
                AnnotationsItem(
                    "foo.py",
                    precedence=PrecedenceType.OVERRIDE,
                    copyright_lines={"Copyright Bob"},
                    spdx_expressions={"CC0-1.0"},
                )
            ],
        )
        toml = NestedReuseTOML(".", [outer, mid, inner])
        assert toml.reuse_info_of("foo/bar/foo.py") == {
            PrecedenceType.AGGREGATE: [
                ReuseInfo(
                    spdx_expressions={_LICENSING.parse("MIT")},
                    copyright_lines={"Copyright Jane Doe"},
                    path="foo/bar/foo.py",
                    source_path="REUSE.toml",
                    source_type=SourceType.REUSE_TOML,
                ),
            ],
            PrecedenceType.OVERRIDE: [
                ReuseInfo(
                    spdx_expressions={_LICENSING.parse("0BSD")},
                    copyright_lines={"Copyright Alice"},
                    path="foo/bar/foo.py",
                    source_path="foo/REUSE.toml",
                    source_type=SourceType.REUSE_TOML,
                ),
            ],
        }

    def test_dont_go_up_hierarchy(self):
        """If a deep REUSE.toml contains instructions for a dir-globbed file,
        don't match against files named as such in parent directories.
        """
        deep = ReuseTOML(
            "src/REUSE.toml",
            1,
            [
                AnnotationsItem(
                    "**/foo.py",
                    precedence=PrecedenceType.CLOSEST,
                    copyright_lines={"Copyright Alice"},
                    spdx_expressions={"0BSD"},
                )
            ],
        )
        toml = NestedReuseTOML(".", [deep])
        assert toml.reuse_info_of("src/foo.py")
        assert toml.reuse_info_of("src/bar/foo.py")
        assert not toml.reuse_info_of("foo.py")
        assert not toml.reuse_info_of("doc/foo.py")

    def test_dont_go_up_directory(self):
        """If a deep REUSE.toml contains an instruction for '../foo.py', don't
        match it against anything.
        """
        deep = ReuseTOML(
            "src/REUSE.toml",
            1,
            [
                AnnotationsItem(
                    "../foo.py",
                    precedence=PrecedenceType.CLOSEST,
                    copyright_lines={"Copyright Alice"},
                    spdx_expressions={"0BSD"},
                )
            ],
        )
        toml = NestedReuseTOML(".", [deep])
        assert not toml.reuse_info_of("src/foo.py")
        assert not toml.reuse_info_of("foo.py")

    def test_aggregate_incomplete_info(self):
        """If one REUSE.toml defines the copyright, and a different one contains
        the licence, then both bits of information should be used.
        """
        outer = ReuseTOML(
            "REUSE.toml",
            1,
            [
                AnnotationsItem(
                    "src/foo.txt",
                    precedence=PrecedenceType.CLOSEST,
                    spdx_expressions={"MIT"},
                )
            ],
        )
        inner = ReuseTOML(
            "src/REUSE.toml",
            1,
            [
                AnnotationsItem(
                    "foo.txt",
                    precedence=PrecedenceType.CLOSEST,
                    copyright_lines={"Copyright Jane Doe"},
                )
            ],
        )
        toml = NestedReuseTOML(".", [outer, inner])
        infos = toml.reuse_info_of("src/foo.txt")[PrecedenceType.CLOSEST]
        assert len(infos) == 2


class TestReuseDep5FromFile:
    """Tests for ReuseDep5.from_file."""

    def test_simple(self, fake_repository_dep5):
        """No error if everything is good."""
        result = ReuseDep5.from_file(fake_repository_dep5 / ".reuse/dep5")
        assert result.__class__ == ReuseDep5
        assert result.dep5_copyright.__class__ == Copyright
        assert result.source == str(fake_repository_dep5 / ".reuse/dep5")

    def test_not_exists(self, empty_directory):
        """Raise FileNotFoundError if .reuse/dep5 doesn't exist."""
        with pytest.raises(FileNotFoundError):
            ReuseDep5.from_file(empty_directory / "foo")

    def test_unicode_decode_error(self, fake_repository_dep5):
        """Raise UnicodeDecodeError if file can't be decoded as utf-8."""
        shutil.copy(
            RESOURCES_DIRECTORY / "fsfe.png", fake_repository_dep5 / "fsfe.png"
        )
        with pytest.raises(UnicodeDecodeError):
            ReuseDep5.from_file(fake_repository_dep5 / "fsfe.png")

    def test_parse_error(self, empty_directory):
        """Raise GlobalLicensingParseError on parse error."""
        (empty_directory / "foo").write_text("foo")
        with pytest.raises(GlobalLicensingParseError):
            ReuseDep5.from_file(empty_directory / "foo")

    def test_double_copyright_parse_error(self, empty_directory):
        """Raise GlobalLicensingParseError on double Copyright lines."""
        (empty_directory / "foo").write_text(
            cleandoc(
                """
                Format: something
                Upstream-Name: example
                Upstream-Contact: Jane Doe
                Source: https://example.com

                Files: *
                Copyright: Jane Doe
                Copyright: John Doe
                License: MIT
                """
            )
        )
        with pytest.raises(GlobalLicensingParseError):
            ReuseDep5.from_file(empty_directory / "foo")


def test_reuse_dep5_reuse_info_of(reuse_dep5):
    """Verify that the glob in the dep5 file is matched."""
    infos = reuse_dep5.reuse_info_of("doc/foo.rst")
    assert len(infos) == 1
    assert len(infos[PrecedenceType.AGGREGATE]) == 1
    result = infos[PrecedenceType.AGGREGATE][0]
    assert LicenseSymbol("CC0-1.0") in result.spdx_expressions
    assert "2017 Jane Doe" in result.copyright_lines


# REUSE-IgnoreEnd
