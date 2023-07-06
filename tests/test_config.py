# SPDX-FileCopyrightText: 2023 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for some _config."""

import os
from inspect import cleandoc
from textwrap import indent
from unittest import mock

from reuse._config import AnnotateOptions, Config

# REUSE-IgnoreStart


def test_annotate_options_merge_one():
    """Replace one attribute."""
    first = AnnotateOptions(
        name="Jane Doe", contact="jane@example.com", license="MIT"
    )
    second = AnnotateOptions(name="John Doe")
    result = first.merge(second)
    assert result.name == second.name
    assert result.contact == first.contact
    assert result.license == first.license


def test_annotate_options_merge_nothing():
    """When merging with an empty AnnotateOptions, do nothing."""
    first = AnnotateOptions(
        name="Jane Doe", contact="jane@example.com", license="MIT"
    )
    second = AnnotateOptions()
    result = first.merge(second)
    assert result == first


def test_annotate_options_merge_all():
    """When merging with a full AnnotateOptions, replace all attributes."""
    first = AnnotateOptions(
        name="Jane Doe", contact="jane@example.com", license="MIT"
    )
    second = AnnotateOptions(
        name="John Doe", contact="john@example.com", license="0BSD"
    )
    result = first.merge(second)
    assert result == second


def test_config_from_dict_global_simple():
    """A simple test case for Config.from_dict."""
    value = {
        "annotate": {
            "default_name": "Jane Doe",
            "default_contact": "jane@example.com",
            "default_license": "MIT",
        }
    }
    result = Config.from_dict(value)
    assert result.global_annotate_options.name == "Jane Doe"
    assert result.global_annotate_options.contact == "jane@example.com"
    assert result.global_annotate_options.license == "MIT"


def test_config_from_dict_global_missing():
    """Only one value is defined."""
    value = {
        "annotate": {
            "default_name": "Jane Doe",
        }
    }
    result = Config.from_dict(value)
    assert result.global_annotate_options.name == "Jane Doe"
    assert result.global_annotate_options.contact is None
    assert result.global_annotate_options.license is None


def test_config_from_dict_override():
    """Overrides are correctly parsed."""
    value = {
        "annotate": {
            "default_name": "Jane Doe",
            "overrides": [
                {
                    "path": "foo",
                    "default_name": "John Doe",
                },
                {
                    "path": "bar",
                    "default_license": "MIT",
                },
            ],
        }
    }
    result = Config.from_dict(value)
    assert result.global_annotate_options.name == "Jane Doe"
    assert result.override_annotate_options["foo"].name == "John Doe"
    assert result.override_annotate_options["bar"].name is None
    assert result.override_annotate_options["bar"].license == "MIT"


def test_config_from_yaml_simple():
    """Load Config from yaml."""
    text = cleandoc(
        """
        annotate:
          default_name: Jane Doe
          default_contact: jane@example.com
          default_license: GPL-3.0-or-later

          overrides:
            - path: ~/Projects/FSFE
              default_contact: jane@fsfe.example.com
        """
    )
    result = Config.from_yaml(text)
    assert result.global_annotate_options.name == "Jane Doe"
    assert result.global_annotate_options.contact == "jane@example.com"
    assert result.global_annotate_options.license == "GPL-3.0-or-later"
    assert (
        result.override_annotate_options["~/Projects/FSFE"].contact
        == "jane@fsfe.example.com"
    )


def test_config_from_yaml_ordered():
    """The override options are ordered by appearance in the yaml file."""
    overrides = []
    for i in range(100):
        overrides.append(
            indent(
                cleandoc(
                    f"""
                    - path: "{i}"
                      default_name: Jane Doe
                    """
                ),
                prefix=" " * 4,
            )
        )
    text = cleandoc(
        """
        annotate:
          overrides:
        {}
        """
    ).format("\n".join(overrides))
    result = Config.from_yaml(text)
    for i, path in enumerate(result.override_annotate_options):
        assert str(i) == path


def test_annotations_for_path_global():
    """When there are no overrides, the annotate options for a given path are
    always the global options.
    """
    options = AnnotateOptions(name="Jane Doe")
    config = Config(global_annotate_options=options)
    result = config.annotations_for_path("foo")
    assert result == options == config.global_annotate_options


def test_annotations_for_path_no_match():
    """When the given path doesn't match any overrides, return the global
    options.
    """
    global_options = AnnotateOptions(name="Jane Doe")
    override_options = AnnotateOptions(name="John Doe")
    config = Config(
        global_annotate_options=global_options,
        override_annotate_options={"~/Projects": override_options},
    )
    result = config.annotations_for_path("/etc/foo")
    assert result == global_options


def test_annotations_for_path_one_match():
    """If one override matches, return the global options merged with the
    override options.
    """
    global_options = AnnotateOptions(name="Jane Doe")
    override_options = AnnotateOptions(contact="jane@example.com")
    config = Config(
        global_annotate_options=global_options,
        override_annotate_options={"/home/jane/Projects": override_options},
    )
    result = config.annotations_for_path(
        "/home/jane/Projects/reuse-tool/README.md"
    )
    assert result.name == "Jane Doe"
    assert result.contact == "jane@example.com"
    assert not result.license


def test_annotations_for_path_expand_home():
    """When the key path of an override starts with '~', expand it when
    checking.
    """
    with mock.patch.dict(os.environ, {"HOME": "/home/jane"}):
        global_options = AnnotateOptions(name="Jane Doe")
        override_options = AnnotateOptions(contact="jane@example.com")
        config = Config(
            global_annotate_options=global_options,
            override_annotate_options={"~/Projects": override_options},
        )
        result = config.annotations_for_path(
            # This path must be manually expanded and cannot start with a '~'.
            "/home/jane/Projects/reuse-tool/README.md"
        )
        assert result.contact == "jane@example.com"


# REUSE-IgnoreEnd
