# SPDX-FileCopyrightText: 2021 Chris Wesseling <chris.wesseling@xs4all.nl>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse._main: init"""

from inspect import cleandoc

from reuse._main import main


def test_init_complete_pyproject_toml(empty_directory, stringio):
    """reuse init should use info from pyproject.toml"""
    repo = empty_directory
    (repo / "pyproject.toml").write_text(
        cleandoc(
            """
        [project]
        name = "fake-repo"
        discription = "Fake Repository"
        authors = [
            {name = "Mary Sue", email = "mary.sue@example.com"}
        ]
        dynamic = ["classifiers"]
        license = {text = "GPL-3.0-or-later"}
        requires-python = ">=3.8"
        [project.urls]
        homepage = "https://example.com"
        """
        )
    )

    result = main(["init"], out=stringio)
    assert result == 0
    assert "What" not in stringio
    assert (
        (repo / ".reuse/dep5").read_text()
        == cleandoc(
            """
            Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
            Upstream-Name: fake-repo
            Upstream-Contact: Mary Sue <mary.sue@example.com>
            Source: https://example.com

            # Sample paragraph, commented out:
            #
            # Files: src/*
            # Copyright: $YEAR $NAME <$CONTACT>
            # License: ...
            """
        )
        + "\n"
    )
