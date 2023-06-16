# SPDX-FileCopyrightText: 2023 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for some _config."""

from reuse._config import Config

# REUSE-IgnoreStart


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


# REUSE-IgnoreEnd
