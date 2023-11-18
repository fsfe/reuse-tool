# SPDX-FileCopyrightText: 2023 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for REUSE.toml."""

from inspect import cleandoc

import pytest
from license_expression import ExpressionError

from reuse._util import _LICENSING
from reuse.reusetoml import AnnotationsItem, ReuseTOML

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
        assert item.precedence == "toml"
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
        assert item.precedence == "toml"
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
        assert item.precedence == "toml"
        assert item.copyright_lines == {"2023 Jane Doe"}
        assert item.spdx_expressions == {_LICENSING.parse("MIT")}

    def test_bad_expr(self):
        """Raise an error on malformed SPDX expressions."""
        with pytest.raises(ExpressionError):
            AnnotationsItem(
                {"foo.py"},
                "toml",
                {"2023 Jane Doe"},
                {"MIT OR"},
            )

    def test_bad_literal(self):
        """Only a limited set of literal are accepted for precedence."""
        with pytest.raises(ValueError):
            AnnotationsItem(
                {"foo.py"},
                "foobar",
                {"2023 Jane Doe"},
                {"MIT"},
            )

    def test_not_str(self):
        """Copyright must be a string."""
        with pytest.raises(TypeError):
            AnnotationsItem(
                {"foo.py"},
                "toml",
                123,
                {"MIT"},
            )

    def test_not_set_of_str(self):
        """Copyright must be a set of strings."""
        with pytest.raises(TypeError):
            AnnotationsItem(
                {"foo.py"},
                "toml",
                {"2023 Jane Doe", 2024},
                {"MIT"},
            )


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
        assert item.precedence == "toml"
        assert item.copyright_lines == {"2023 Jane Doe"}
        assert item.spdx_expressions == {_LICENSING.parse("MIT")}

    def test_trigger_validators(self):
        """It's possible to trigger the validators by providing a bad value."""
        with pytest.raises(TypeError):
            AnnotationsItem.from_dict(
                {
                    "path": {123},
                    "precedence": "toml",
                    "SPDX-FileCopyrightText": {"2023 Jane Doe"},
                    "SPDX-License-Identifier": {"MIT"},
                }
            )

    def test_missing(self):
        """If a key is missing, raise an error."""
        with pytest.raises(TypeError):
            AnnotationsItem.from_dict(
                {
                    "precedence": "toml",
                    "SPDX-FileCopyrightText": {"2023 Jane Doe"},
                    "SPDX-License-Identifier": {"MIT"},
                }
            )

    def test_none(self):
        """If a key is None, raise an error."""
        with pytest.raises(TypeError):
            AnnotationsItem.from_dict(
                {
                    "path": None,
                    "precedence": "toml",
                    "SPDX-FileCopyrightText": {"2023 Jane Doe"},
                    "SPDX-License-Identifier": {"MIT"},
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
        with pytest.raises(TypeError):
            ReuseTOML(
                version=1.2, source="REUSE.toml", annotations=[annotations_item]
            )

    def test_source_not_str(self, annotations_item):
        """Source must be a str."""
        with pytest.raises(TypeError):
            ReuseTOML(version=1, source=123, annotations=[annotations_item])

    def test_annotations_must_be_list(self, annotations_item):
        """Annotations must be in a list, not any other collection."""
        # TODO: Technically we could change this to 'any collection that is
        # ordered', but let's not split hairs.
        with pytest.raises(TypeError):
            ReuseTOML(
                version=1, source="REUSE.toml", annotations={annotations_item}
            )

    def test_annotations_must_be_object(self):
        """Annotations must be AnnotationsItem objects."""
        with pytest.raises(TypeError):
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
        with pytest.raises(TypeError):
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


# REUSE-IgnoreEnd
