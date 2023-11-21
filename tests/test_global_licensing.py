# SPDX-FileCopyrightText: 2023 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for REUSE.toml and .reuse/dep5."""

import shutil
from inspect import cleandoc

import pytest
from conftest import RESOURCES_DIRECTORY
from debian.copyright import Copyright
from license_expression import LicenseSymbol

from reuse import ReuseInfo, SourceType
from reuse._util import _LICENSING
from reuse.global_licensing import (
    AnnotationsItem,
    GlobalLicensingParseError,
    GlobalLicensingParseTypeError,
    GlobalLicensingParseValueError,
    GlobalPrecedence,
    ReuseDep5,
    ReuseTOML,
)

# REUSE-IgnoreStart

# pylint: disable=redefined-outer-name


@pytest.fixture()
def annotations_item():
    return AnnotationsItem({"foo.py"}, "toml", {"2023 Jane Doe"}, {"MIT"})


class TestAnnotationsItemValidators:
    """Test the validators of AnnotationsItem."""

    def test_simple(self):
        """Create an AnnotationsItem, passing all validators."""
        item = AnnotationsItem(
            {"foo.py"},
            "toml",
            {"2023 Jane Doe"},
            {"MIT"},
        )
        assert item.paths == {"foo.py"}
        assert item.precedence == GlobalPrecedence.TOML
        assert item.copyright_lines == {"2023 Jane Doe"}
        assert item.spdx_expressions == {_LICENSING.parse("MIT")}

    def test_from_list(self):
        """Convert lists to sets."""
        item = AnnotationsItem(
            ["foo.py"],
            "toml",
            ["2023 Jane Doe"],
            ["MIT"],
        )
        assert item.paths == {"foo.py"}
        assert item.precedence == GlobalPrecedence.TOML
        assert item.copyright_lines == {"2023 Jane Doe"}
        assert item.spdx_expressions == {_LICENSING.parse("MIT")}

    def test_str_to_set(self):
        """Convert strings to sets."""
        item = AnnotationsItem(
            "foo.py",
            "toml",
            "2023 Jane Doe",
            "MIT",
        )
        assert item.paths == {"foo.py"}
        assert item.precedence == GlobalPrecedence.TOML
        assert item.copyright_lines == {"2023 Jane Doe"}
        assert item.spdx_expressions == {_LICENSING.parse("MIT")}

    def test_bad_expr(self):
        """Raise an error on malformed SPDX expressions."""
        with pytest.raises(GlobalLicensingParseError):
            AnnotationsItem(
                {"foo.py"},
                "toml",
                {"2023 Jane Doe"},
                {"MIT OR"},
            )

    def test_bad_literal(self):
        """Only a limited set of literal are accepted for precedence."""
        with pytest.raises(GlobalLicensingParseValueError):
            AnnotationsItem(
                {"foo.py"},
                "foobar",
                {"2023 Jane Doe"},
                {"MIT"},
            )

    def test_not_str(self):
        """Copyright must be a string."""
        with pytest.raises(GlobalLicensingParseTypeError):
            AnnotationsItem(
                {"foo.py"},
                "toml",
                123,
                {"MIT"},
            )

    def test_not_set_of_str(self):
        """Copyright must be a set of strings."""
        with pytest.raises(GlobalLicensingParseTypeError):
            AnnotationsItem(
                {"foo.py"},
                "toml",
                {"2023 Jane Doe", 2024},
                {"MIT"},
            )

    def test_paths_must_not_be_empty(self):
        """'paths' may not be an empty list."""
        with pytest.raises(GlobalLicensingParseValueError):
            AnnotationsItem(
                set(),
                "toml",
                {"2023 Jane Doe"},
                {"MIT"},
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
                "precedence": "toml",
                "SPDX-FileCopyrightText": {"2023 Jane Doe"},
                "SPDX-License-Identifier": {"MIT"},
            }
        )
        assert item.paths == {"foo.py"}
        assert item.precedence == GlobalPrecedence.TOML
        assert item.copyright_lines == {"2023 Jane Doe"}
        assert item.spdx_expressions == {_LICENSING.parse("MIT")}

    def test_trigger_validators(self):
        """It's possible to trigger the validators by providing a bad value."""
        with pytest.raises(GlobalLicensingParseTypeError):
            AnnotationsItem.from_dict(
                {
                    "path": {123},
                    "precedence": "toml",
                    "SPDX-FileCopyrightText": {"2023 Jane Doe"},
                    "SPDX-License-Identifier": {"MIT"},
                }
            )

    def test_path_missing(self):
        """If the path key is missing, raise an error."""
        with pytest.raises(GlobalLicensingParseValueError):
            AnnotationsItem.from_dict(
                {
                    "precedence": "toml",
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
                    "precedence": "toml",
                    "SPDX-FileCopyrightText": {"2023 Jane Doe"},
                    "SPDX-License-Identifier": {"MIT"},
                }
            )

    def test_one_key_missing(self):
        """If one REUSE info key is missing, raise no error."""
        item = AnnotationsItem.from_dict(
            {
                "path": {"foo.py"},
                "precedence": "toml",
                "SPDX-License-Identifier": {"MIT"},
            }
        )
        assert not item.copyright_lines
        assert isinstance(item.copyright_lines, set)

    def test_both_keys_missing(self):
        """If both REUSE info keys are missing, raise an error."""
        with pytest.raises(GlobalLicensingParseValueError):
            AnnotationsItem.from_dict(
                {
                    "path": {"foo.py"},
                    "precedence": "toml",
                }
            )


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
                        "precedence": "toml",
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
                            "precedence": "toml",
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
            precedence = "toml"
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


class TestReuseTOMLReuseInfoOf:
    """Test the reuse_info_of method of ReuseTOML."""

    def test_simple(self, annotations_item):
        reuse_toml = ReuseTOML("REUSE.toml", 1, [annotations_item])
        assert reuse_toml.reuse_info_of("foo.py") == ReuseInfo(
            spdx_expressions={_LICENSING.parse("MIT")},
            copyright_lines={"2023 Jane Doe"},
            path="foo.py",
            source_path="REUSE.toml",
            source_type=SourceType.REUSE_TOML,
        )

    def test_latest_annotations_item(self, annotations_item):
        """If two items match, use exclusively the latest."""
        reuse_toml = ReuseTOML(
            "REUSE.toml",
            1,
            [
                annotations_item,
                AnnotationsItem(
                    paths={"foo.py"},
                    precedence="toml",
                    copyright_lines={"2023 John Doe"},
                    spdx_expressions={"0BSD"},
                ),
            ],
        )
        assert reuse_toml.reuse_info_of("foo.py") == ReuseInfo(
            spdx_expressions={_LICENSING.parse("0BSD")},
            copyright_lines={"2023 John Doe"},
            path="foo.py",
            source_path="REUSE.toml",
            source_type=SourceType.REUSE_TOML,
        )

    def test_glob_all(self):
        """When globbing all, match everything."""
        reuse_toml = ReuseTOML(
            "REUSE.toml",
            1,
            [
                AnnotationsItem(
                    paths={"*"},
                    precedence="toml",
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
        assert reuse_toml.reuse_info_of("foo.py") == expected.copy(
            path="foo.py"
        )
        assert reuse_toml.reuse_info_of("bar.py") == expected.copy(
            path="bar.py"
        )
        assert reuse_toml.reuse_info_of("dir/subdir/foo.py") == expected.copy(
            path="dir/subdir/foo.py"
        )

    def test_glob_py(self):
        """When globbing Python paths, match only .py files."""
        reuse_toml = ReuseTOML(
            "REUSE.toml",
            1,
            [
                AnnotationsItem(
                    paths={"*.py"},
                    precedence="toml",
                    copyright_lines={"2023 Jane Doe"},
                    spdx_expressions={"MIT"},
                ),
            ],
        )
        assert reuse_toml.reuse_info_of("dir/foo.py") == ReuseInfo(
            spdx_expressions={_LICENSING.parse("MIT")},
            copyright_lines={"2023 Jane Doe"},
            path="dir/foo.py",
            source_path="REUSE.toml",
            source_type=SourceType.REUSE_TOML,
        )
        assert reuse_toml.reuse_info_of("foo.c") == ReuseInfo()


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
                precedence = "toml"
                SPDX-FileCopyrightText = "2023 Jane Doe"
                SPDX-License-Identifier = "MIT"
                """
            )
        )
        result = ReuseTOML.from_file("REUSE.toml")
        assert result.version == 1
        assert result.source == "REUSE.toml"
        assert result.annotations[0] == annotations_item


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
    result = reuse_dep5.reuse_info_of("doc/foo.rst")
    assert LicenseSymbol("CC0-1.0") in result.spdx_expressions
    assert "2017 Jane Doe" in result.copyright_lines


# REUSE-IgnoreEnd
