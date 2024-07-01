# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2019 Stefan Bakker <s.bakker777@gmail.com>
# SPDX-FileCopyrightText: 2022 Carmen Bianca Bakker <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2023 Maxim Cournoyer <maxim.cournoyer@gmail.com>
# SPDX-FileCopyrightText: 2024 Rivos Inc.
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse._main: annotate"""
import logging
import stat
from inspect import cleandoc

import pytest

from reuse._main import main

# pylint: disable=too-many-lines,unused-argument


# REUSE-IgnoreStart


# TODO: Replace this test with a monkeypatched test
def test_annotate_simple(fake_repository, stringio, mock_date_today):
    """Add a header to a file that does not have one."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")
    expected = cleandoc(
        """
        # SPDX-FileCopyrightText: 2018 Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later

        pass
        """
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert simple_file.read_text() == expected


def test_annotate_simple_scheme(fake_repository, stringio, mock_date_today):
    "Add a header to a Scheme file."
    simple_file = fake_repository / "foo.scm"
    simple_file.write_text("#t")
    expected = cleandoc(
        """
        ;;; SPDX-FileCopyrightText: 2018 Jane Doe
        ;;;
        ;;; SPDX-License-Identifier: GPL-3.0-or-later

        #t
        """
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "foo.scm",
        ],
        out=stringio,
    )

    assert result == 0
    assert simple_file.read_text() == expected


def test_annotate_scheme_standardised(
    fake_repository, stringio, mock_date_today
):
    """The comment block is rewritten/standardised."""
    simple_file = fake_repository / "foo.scm"
    simple_file.write_text(
        cleandoc(
            """
            ; SPDX-FileCopyrightText: 2018 Jane Doe
            ;
            ; SPDX-License-Identifier: GPL-3.0-or-later

            #t
            """
        )
    )
    expected = cleandoc(
        """
        ;;; SPDX-FileCopyrightText: 2018 Jane Doe
        ;;;
        ;;; SPDX-License-Identifier: GPL-3.0-or-later

        #t
        """
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "foo.scm",
        ],
        out=stringio,
    )

    assert result == 0
    assert simple_file.read_text() == expected


def test_annotate_scheme_standardised2(
    fake_repository, stringio, mock_date_today
):
    """The comment block is rewritten/standardised."""
    simple_file = fake_repository / "foo.scm"
    simple_file.write_text(
        cleandoc(
            """
            ;; SPDX-FileCopyrightText: 2018 Jane Doe
            ;;
            ;; SPDX-License-Identifier: GPL-3.0-or-later

            #t
            """
        )
    )
    expected = cleandoc(
        """
        ;;; SPDX-FileCopyrightText: 2018 Jane Doe
        ;;;
        ;;; SPDX-License-Identifier: GPL-3.0-or-later

        #t
        """
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "foo.scm",
        ],
        out=stringio,
    )

    assert result == 0
    assert simple_file.read_text() == expected


def test_annotate_simple_no_replace(fake_repository, stringio, mock_date_today):
    """Add a header to a file without replacing the existing header."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text(
        cleandoc(
            """
            # SPDX-FileCopyrightText: 2017 John Doe
            #
            # SPDX-License-Identifier: MIT

            pass
            """
        )
    )
    expected = cleandoc(
        """
        # SPDX-FileCopyrightText: 2018 Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later

        # SPDX-FileCopyrightText: 2017 John Doe
        #
        # SPDX-License-Identifier: MIT

        pass
        """
    )

    result = main(
        [
            "annotate",
            "--no-replace",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert simple_file.read_text() == expected


def test_annotate_year(fake_repository, stringio):
    """Add a header to a file with a custom year."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")
    expected = cleandoc(
        """
        # SPDX-FileCopyrightText: 2016 Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later

        pass
        """
    )

    result = main(
        [
            "annotate",
            "--year",
            "2016",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert simple_file.read_text() == expected


def test_annotate_no_year(fake_repository, stringio):
    """Add a header to a file without a year."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")
    expected = cleandoc(
        """
        # SPDX-FileCopyrightText: Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later

        pass
        """
    )

    result = main(
        [
            "annotate",
            "--exclude-year",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert simple_file.read_text() == expected


@pytest.mark.parametrize(
    "copyright_prefix", ["--copyright-prefix", "--copyright-style"]
)
def test_annotate_copyright_prefix(
    fake_repository, copyright_prefix, stringio, mock_date_today
):
    """Add a header with a specific copyright prefix. Also test the old name of
    the parameter.
    """
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")
    expected = cleandoc(
        """
        # Copyright 2018 Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later

        pass
        """
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            copyright_prefix,
            "string",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert simple_file.read_text() == expected


def test_annotate_shebang(fake_repository, stringio):
    """Keep the shebang when annotating."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text(
        cleandoc(
            """
            #!/usr/bin/env python3

            pass
            """
        )
    )
    expected = cleandoc(
        """
        #!/usr/bin/env python3

        # SPDX-License-Identifier: GPL-3.0-or-later

        pass
        """
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert simple_file.read_text() == expected


def test_annotate_shebang_wrong_comment_style(fake_repository, stringio):
    """If a comment style does not support the shebang at the top, don't treat
    the shebang as special.
    """
    simple_file = fake_repository / "foo.html"
    simple_file.write_text(
        cleandoc(
            """
            #!/usr/bin/env python3

            pass
            """
        )
    )
    expected = cleandoc(
        """
        <!--
        SPDX-License-Identifier: GPL-3.0-or-later
        -->

        #!/usr/bin/env python3

        pass
        """
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "foo.html",
        ],
        out=stringio,
    )

    assert result == 0
    assert simple_file.read_text() == expected


def test_annotate_contributors_only(
    fake_repository, stringio, mock_date_today, contributors
):
    """Add a header with only contributor information."""

    if not contributors:
        pytest.skip("No contributors to add")

    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")
    content = []

    for contributor in sorted(contributors):
        content.append(f"# SPDX-FileContributor: {contributor}")

    content += ["", "pass"]
    expected = cleandoc("\n".join(content))

    args = [
        "annotate",
    ]
    for contributor in contributors:
        args += ["--contributor", contributor]
    args += ["foo.py"]

    result = main(
        args,
        out=stringio,
    )

    assert result == 0
    assert simple_file.read_text() == expected


def test_annotate_contributors(
    fake_repository, stringio, mock_date_today, contributors
):
    """Add a header with contributor information."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")
    content = ["# SPDX-FileCopyrightText: 2018 Jane Doe"]

    if contributors:
        for contributor in sorted(contributors):
            content.append(f"# SPDX-FileContributor: {contributor}")

    content += ["#", "# SPDX-License-Identifier: GPL-3.0-or-later", "", "pass"]
    expected = cleandoc("\n".join(content))

    args = [
        "annotate",
        "--license",
        "GPL-3.0-or-later",
        "--copyright",
        "Jane Doe",
    ]
    for contributor in contributors:
        args += ["--contributor", contributor]
    args += ["foo.py"]

    result = main(
        args,
        out=stringio,
    )

    assert result == 0
    assert simple_file.read_text() == expected


def test_annotate_specify_style(fake_repository, stringio, mock_date_today):
    """Add a header to a file that does not have one, using a custom style."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")
    expected = cleandoc(
        """
        // SPDX-FileCopyrightText: 2018 Jane Doe
        //
        // SPDX-License-Identifier: GPL-3.0-or-later

        pass
        """
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "--style",
            "cpp",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert simple_file.read_text() == expected


def test_annotate_specify_style_unrecognised(
    fake_repository, stringio, mock_date_today
):
    """Add a header to a file that is unrecognised."""

    simple_file = fake_repository / "hello.foo"
    simple_file.touch()
    expected = "# SPDX-FileCopyrightText: 2018 Jane Doe"

    result = main(
        [
            "annotate",
            "--copyright",
            "Jane Doe",
            "--style",
            "python",
            "hello.foo",
        ],
        out=stringio,
    )

    assert result == 0
    assert simple_file.read_text().strip() == expected


def test_annotate_implicit_style(fake_repository, stringio, mock_date_today):
    """Add a header to a file that has a recognised extension."""
    simple_file = fake_repository / "foo.js"
    simple_file.write_text("pass")
    expected = cleandoc(
        """
        // SPDX-FileCopyrightText: 2018 Jane Doe
        //
        // SPDX-License-Identifier: GPL-3.0-or-later

        pass
        """
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "foo.js",
        ],
        out=stringio,
    )

    assert result == 0
    assert simple_file.read_text() == expected


def test_annotate_implicit_style_filename(
    fake_repository, stringio, mock_date_today
):
    """Add a header to a filename that is recognised."""
    simple_file = fake_repository / "Makefile"
    simple_file.write_text("pass")
    expected = cleandoc(
        """
        # SPDX-FileCopyrightText: 2018 Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later

        pass
        """
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "Makefile",
        ],
        out=stringio,
    )

    assert result == 0
    assert simple_file.read_text() == expected


def test_annotate_unrecognised_style(fake_repository, capsys):
    """Add a header to a file that has an unrecognised extension."""
    simple_file = fake_repository / "foo.foo"
    simple_file.write_text("pass")

    with pytest.raises(SystemExit):
        main(
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "foo.foo",
            ],
        )

    stdout = capsys.readouterr().err
    assert (
        "The following files do not have a recognised file extension" in stdout
    )
    assert "foo.foo" in stdout


@pytest.mark.parametrize(
    "skip_unrecognised", ["--skip-unrecognised", "--skip-unrecognized"]
)
def test_annotate_skip_unrecognised(
    fake_repository, skip_unrecognised, stringio
):
    """Skip file that has an unrecognised extension."""
    simple_file = fake_repository / "foo.foo"
    simple_file.write_text("pass")

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            skip_unrecognised,
            "foo.foo",
        ],
        out=stringio,
    )

    assert result == 0
    assert "Skipped unrecognised file 'foo.foo'" in stringio.getvalue()


def test_annotate_skip_unrecognised_and_style(
    fake_repository, stringio, caplog
):
    """--skip-unrecognised and --style show warning message."""
    simple_file = fake_repository / "foo.foo"
    simple_file.write_text("pass")

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "--style=c",
            "--skip-unrecognised",
            "foo.foo",
        ],
        out=stringio,
    )

    assert result == 0
    loglevel = logging.getLogger("reuse").level
    if loglevel > logging.WARNING:
        pytest.skip(
            "Test needs LogLevel <= WARNING (e.g. WARNING, INFO, DEBUG)."
        )
    else:
        assert "no effect" in caplog.text


def test_annotate_no_copyright_or_license(fake_repository):
    """Add a header, but supply no copyright or license."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")

    with pytest.raises(SystemExit):
        main(["annotate", "foo.py"])


def test_annotate_template_simple(
    fake_repository, stringio, mock_date_today, template_simple_source
):
    """Add a header with a custom template."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")
    template_file = fake_repository / ".reuse/templates/mytemplate.jinja2"
    template_file.parent.mkdir(parents=True, exist_ok=True)
    template_file.write_text(template_simple_source)
    expected = cleandoc(
        """
        # Hello, world!
        #
        # SPDX-FileCopyrightText: 2018 Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later

        pass
        """
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "--template",
            "mytemplate.jinja2",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert simple_file.read_text() == expected


def test_annotate_template_simple_multiple(
    fake_repository, stringio, mock_date_today, template_simple_source
):
    """Add a header with a custom template to multiple files."""
    simple_files = [fake_repository / f"foo{i}.py" for i in range(10)]
    for simple_file in simple_files:
        simple_file.write_text("pass")
    template_file = fake_repository / ".reuse/templates/mytemplate.jinja2"
    template_file.parent.mkdir(parents=True, exist_ok=True)
    template_file.write_text(template_simple_source)

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "--template",
            "mytemplate.jinja2",
        ]
        + list(map(str, simple_files)),
        out=stringio,
    )

    assert result == 0
    for simple_file in simple_files:
        expected = cleandoc(
            """
            # Hello, world!
            #
            # SPDX-FileCopyrightText: 2018 Jane Doe
            #
            # SPDX-License-Identifier: GPL-3.0-or-later

            pass
            """
        )
        assert simple_file.read_text() == expected


def test_annotate_template_no_spdx(
    fake_repository, stringio, template_no_spdx_source
):
    """Add a header with a template that lacks REUSE info."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")
    template_file = fake_repository / ".reuse/templates/mytemplate.jinja2"
    template_file.parent.mkdir(parents=True, exist_ok=True)
    template_file.write_text(template_no_spdx_source)

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "--template",
            "mytemplate.jinja2",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 1


def test_annotate_template_commented(
    fake_repository, stringio, mock_date_today, template_commented_source
):
    """Add a header with a custom template that is already commented."""
    simple_file = fake_repository / "foo.c"
    simple_file.write_text("pass")
    template_file = (
        fake_repository / ".reuse/templates/mytemplate.commented.jinja2"
    )
    template_file.parent.mkdir(parents=True, exist_ok=True)
    template_file.write_text(template_commented_source)
    expected = cleandoc(
        """
        # Hello, world!
        #
        # SPDX-FileCopyrightText: 2018 Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later

        pass
        """
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "--template",
            "mytemplate.commented.jinja2",
            "foo.c",
        ],
        out=stringio,
    )

    assert result == 0
    assert simple_file.read_text() == expected


def test_annotate_template_nonexistant(fake_repository):
    """Raise an error when using a header that does not exist."""

    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")

    with pytest.raises(SystemExit):
        main(
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "--template",
                "mytemplate.jinja2",
                "foo.py",
            ]
        )


def test_annotate_template_without_extension(
    fake_repository, stringio, mock_date_today, template_simple_source
):
    """Find the correct header even when not using an extension."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")
    template_file = fake_repository / ".reuse/templates/mytemplate.jinja2"
    template_file.parent.mkdir(parents=True, exist_ok=True)
    template_file.write_text(template_simple_source)
    expected = cleandoc(
        """
        # Hello, world!
        #
        # SPDX-FileCopyrightText: 2018 Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later

        pass
        """
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "--template",
            "mytemplate",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert simple_file.read_text() == expected


def test_annotate_binary(
    fake_repository, stringio, mock_date_today, binary_string
):
    """Add a header to a .license file if the file is a binary."""
    binary_file = fake_repository / "foo.png"
    binary_file.write_bytes(binary_string)
    expected = cleandoc(
        """
        SPDX-FileCopyrightText: 2018 Jane Doe

        SPDX-License-Identifier: GPL-3.0-or-later
        """
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "foo.png",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        binary_file.with_name(f"{binary_file.name}.license").read_text().strip()
        == expected
    )


def test_annotate_uncommentable_json(
    fake_repository, stringio, mock_date_today
):
    """Add a header to a .license file if the file is uncommentable, e.g.,
    JSON.
    """
    json_file = fake_repository / "foo.json"
    json_file.write_text('{"foo": 23, "bar": 42}')
    expected = cleandoc(
        """
        SPDX-FileCopyrightText: 2018 Jane Doe

        SPDX-License-Identifier: GPL-3.0-or-later
        """
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "foo.json",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        json_file.with_name(f"{json_file.name}.license").read_text().strip()
        == expected
    )


def test_annotate_fallback_dot_license(
    fake_repository, stringio, mock_date_today
):
    """Add a header to .license if --fallback-dot-license is given, and no style
    yet exists.
    """
    (fake_repository / "foo.py").write_text("Foo")
    (fake_repository / "foo.foo").write_text("Foo")

    expected_py = cleandoc(
        """
        # SPDX-FileCopyrightText: 2018 Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later
        """
    )
    expected_foo = cleandoc(
        """
        SPDX-FileCopyrightText: 2018 Jane Doe

        SPDX-License-Identifier: GPL-3.0-or-later
        """
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "--fallback-dot-license",
            "foo.py",
            "foo.foo",
        ],
        out=stringio,
    )

    assert result == 0
    assert expected_py in (fake_repository / "foo.py").read_text()
    assert (fake_repository / "foo.foo.license").exists()
    assert (
        fake_repository / "foo.foo.license"
    ).read_text().strip() == expected_foo
    assert (
        "'foo.foo' is not recognised; creating 'foo.foo.license'"
        in stringio.getvalue()
    )


def test_annotate_force_dot_license(fake_repository, stringio, mock_date_today):
    """Add a header to a .license file if --force-dot-license is given."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")
    expected = cleandoc(
        """
        SPDX-FileCopyrightText: 2018 Jane Doe

        SPDX-License-Identifier: GPL-3.0-or-later
        """
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "--force-dot-license",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        simple_file.with_name(f"{simple_file.name}.license").read_text().strip()
        == expected
    )
    assert simple_file.read_text() == "pass"


def test_annotate_force_dot_license_double(
    fake_repository, stringio, mock_date_today
):
    """When path.license already exists, don't create path.license.license."""
    simple_file = fake_repository / "foo.txt"
    simple_file_license = fake_repository / "foo.txt.license"
    simple_file_license_license = fake_repository / "foo.txt.license.license"

    simple_file.write_text("foo")
    simple_file_license.write_text("foo")
    expected = cleandoc(
        """
        SPDX-FileCopyrightText: 2018 Jane Doe

        SPDX-License-Identifier: GPL-3.0-or-later
        """
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "--force-dot-license",
            "foo.txt",
        ],
        out=stringio,
    )

    assert result == 0
    assert not simple_file_license_license.exists()
    assert simple_file_license.read_text().strip() == expected


def test_annotate_force_dot_license_unsupported_filetype(
    fake_repository, stringio, mock_date_today
):
    """Add a header to a .license file if --force-dot-license is given, with the
    base file being an otherwise unsupported filetype.
    """
    simple_file = fake_repository / "foo.txt"
    simple_file.write_text("Preserve this")
    expected = cleandoc(
        """
        SPDX-FileCopyrightText: 2018 Jane Doe

        SPDX-License-Identifier: GPL-3.0-or-later
        """
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "--force-dot-license",
            "foo.txt",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        simple_file.with_name(f"{simple_file.name}.license").read_text().strip()
        == expected
    )
    assert simple_file.read_text() == "Preserve this"


def test_annotate_force_dot_license_doesnt_write_to_file(
    fake_repository, stringio, mock_date_today
):
    """Adding a header to a .license file if --force-dot-license is given,
    doesn't require write permission to the file, just the directory.
    """
    simple_file = fake_repository / "foo.txt"
    simple_file.write_text("Preserve this")
    simple_file.chmod(mode=stat.S_IREAD)
    expected = cleandoc(
        """
        SPDX-FileCopyrightText: 2018 Jane Doe

        SPDX-License-Identifier: GPL-3.0-or-later
        """
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "--force-dot-license",
            "foo.txt",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        simple_file.with_name(f"{simple_file.name}.license").read_text().strip()
        == expected
    )
    assert simple_file.read_text() == "Preserve this"


def test_annotate_to_read_only_file_does_not_traceback(
    fake_repository, stringio, mock_date_today
):
    """Trying to add a header without having write permission, shouldn't result
    in a traceback. See issue #398"""
    _file = fake_repository / "test.sh"
    _file.write_text("#!/bin/sh")
    _file.chmod(mode=stat.S_IREAD)
    with pytest.raises(SystemExit) as info:
        main(
            [
                "annotate",
                "--license",
                "Apache-2.0",
                "--copyright",
                "mycorp",
                "--style",
                "python",
                "test.sh",
            ]
        )
    assert info.value  # should not exit with 0


def test_annotate_license_file(fake_repository, stringio, mock_date_today):
    """Add a header to a .license file if it exists."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("foo")
    license_file = fake_repository / "foo.py.license"
    license_file.write_text(
        cleandoc(
            """
            SPDX-FileCopyrightText: 2016 John Doe

            Hello
            """
        )
    )
    expected = (
        cleandoc(
            """
            SPDX-FileCopyrightText: 2016 John Doe
            SPDX-FileCopyrightText: 2018 Jane Doe

            SPDX-License-Identifier: GPL-3.0-or-later
            """
        )
        + "\n"
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert license_file.read_text() == expected
    assert simple_file.read_text() == "foo"


def test_annotate_license_file_only_one_newline(
    fake_repository, stringio, mock_date_today
):
    """When a header is added to a .license file that already ends with a
    newline, the new header should end with a single newline.
    """
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("foo")
    license_file = fake_repository / "foo.py.license"
    license_file.write_text(
        cleandoc(
            """
            SPDX-FileCopyrightText: 2016 John Doe

            Hello
            """
        )
        + "\n"
    )
    expected = (
        cleandoc(
            """
            SPDX-FileCopyrightText: 2016 John Doe
            SPDX-FileCopyrightText: 2018 Jane Doe

            SPDX-License-Identifier: GPL-3.0-or-later
            """
        )
        + "\n"
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert license_file.read_text() == expected
    assert simple_file.read_text() == "foo"


def test_annotate_year_mutually_exclusive(fake_repository):
    """--exclude-year and --year are mutually exclusive."""
    with pytest.raises(SystemExit):
        main(
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "--exclude-year",
                "--year",
                "2020",
                "src/source_code.py",
            ]
        )


def test_annotate_single_multi_line_mutually_exclusive(fake_repository):
    """--single-line and --multi-line are mutually exclusive."""
    with pytest.raises(SystemExit):
        main(
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "--single-line",
                "--multi-line",
                "src/source_code.c",
            ]
        )


def test_annotate_skip_force_mutually_exclusive(fake_repository):
    """--skip-unrecognised and --force-dot-license are mutually exclusive."""
    with pytest.raises(SystemExit):
        main(
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "--force-dot-license",
                "--skip-unrecognised",
                "src/source_code.py",
            ]
        )


def test_annotate_multi_line_not_supported(fake_repository):
    """Expect a fail if --multi-line is not supported for a file type."""
    with pytest.raises(SystemExit):
        main(
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "--multi-line",
                "src/source_code.py",
            ]
        )


def test_annotate_multi_line_not_supported_custom_style(
    fake_repository, capsys
):
    """--multi-line also fails when used with a style that doesn't support it
    through --style.
    """
    (fake_repository / "foo.foo").write_text("foo")
    with pytest.raises(SystemExit):
        main(
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "--multi-line",
                "--force-dot-license",
                "--style",
                "python",
                "foo.foo",
            ],
        )

    assert "'foo.foo' does not support multi-line" in capsys.readouterr().err


def test_annotate_single_line_not_supported(fake_repository):
    """Expect a fail if --single-line is not supported for a file type."""
    with pytest.raises(SystemExit):
        main(
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "--single-line",
                "src/source_code.html",
            ]
        )


def test_annotate_force_multi_line_for_c(
    fake_repository, stringio, mock_date_today
):
    """--multi-line forces a multi-line comment for C."""
    simple_file = fake_repository / "foo.c"
    simple_file.write_text("foo")
    expected = cleandoc(
        """
                /*
                 * SPDX-FileCopyrightText: 2018 Jane Doe
                 *
                 * SPDX-License-Identifier: GPL-3.0-or-later
                 */

                foo
                """
    )

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "--multi-line",
            "foo.c",
        ],
        out=stringio,
    )

    assert result == 0
    assert simple_file.read_text() == expected


@pytest.mark.parametrize("line_ending", ["\r\n", "\r", "\n"])
def test_annotate_line_endings(
    empty_directory, stringio, mock_date_today, line_ending
):
    """Given a file with a certain type of line ending, preserve it."""
    simple_file = empty_directory / "foo.py"
    simple_file.write_bytes(
        line_ending.encode("utf-8").join([b"hello", b"world"])
    )
    expected = cleandoc(
        """
            # SPDX-FileCopyrightText: 2018 Jane Doe
            #
            # SPDX-License-Identifier: GPL-3.0-or-later

            hello
            world
            """
    ).replace("\n", line_ending)

    result = main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    with open(simple_file, newline="", encoding="utf-8") as fp:
        contents = fp.read()

    assert contents == expected


def test_annotate_skip_existing(fake_repository, stringio, mock_date_today):
    """When annotate --skip-existing on a file that already contains REUSE info,
    don't write additional information to it.
    """
    for path in ("foo.py", "bar.py"):
        (fake_repository / path).write_text("pass")
    expected_foo = cleandoc(
        """
        # SPDX-FileCopyrightText: 2018 Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later

        pass
        """
    )
    expected_bar = cleandoc(
        """
        # SPDX-FileCopyrightText: 2018 John Doe
        #
        # SPDX-License-Identifier: MIT

        pass
        """
    )

    main(
        [
            "annotate",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Jane Doe",
            "foo.py",
        ],
        out=stringio,
    )

    result = main(
        [
            "annotate",
            "--license",
            "MIT",
            "--copyright",
            "John Doe",
            "--skip-existing",
            "foo.py",
            "bar.py",
        ]
    )

    assert result == 0
    assert (fake_repository / "foo.py").read_text() == expected_foo
    assert (fake_repository / "bar.py").read_text() == expected_bar


def test_annotate_recursive(fake_repository, stringio, mock_date_today):
    """Add a header to a directory recursively."""
    (fake_repository / "src/one/two").mkdir(parents=True)
    (fake_repository / "src/one/two/foo.py").write_text(
        cleandoc(
            """
            # SPDX-License-Identifier: GPL-3.0-or-later
            """
        )
    )
    (fake_repository / "src/hello.py").touch()
    (fake_repository / "src/one/world.py").touch()
    (fake_repository / "bar").mkdir(parents=True)
    (fake_repository / "bar/bar.py").touch()

    result = main(
        [
            "annotate",
            "--copyright",
            "Joe Somebody",
            "--recursive",
            "src/",
        ],
        out=stringio,
    )

    for path in (fake_repository / "src").rglob("src/**"):
        content = path.read_text()
        assert "SPDX-FileCopyrightText: 2018 Joe Somebody" in content

    assert "Joe Somebody" not in (fake_repository / "bar/bar.py").read_text()
    assert result == 0


def test_annotate_recursive_on_file(fake_repository, stringio, mock_date_today):
    """Don't expect errors when annotate is run 'recursively' on a file."""
    result = main(
        [
            "annotate",
            "--copyright",
            "Joe Somebody",
            "--recursive",
            "src/source_code.py",
        ],
        out=stringio,
    )

    assert (
        "Joe Somebody" in (fake_repository / "src/source_code.py").read_text()
    )
    assert result == 0


def test_annotate_exit_if_unrecognised(
    fake_repository, stringio, mock_date_today
):
    """Expect error and no edited files if at least one file has not been
    recognised, with --exit-if-unrecognised enabled."""
    (fake_repository / "baz").mkdir(parents=True)
    (fake_repository / "baz/foo.py").write_text("foo")
    (fake_repository / "baz/bar.unknown").write_text("bar")
    (fake_repository / "baz/baz.sh").write_text("baz")

    with pytest.raises(SystemExit):
        main(
            [
                "annotate",
                "--license",
                "Apache-2.0",
                "--copyright",
                "Jane Doe",
                "--recursive",
                "--exit-if-unrecognised",
                "baz/",
            ]
        )

    assert "Jane Doe" not in (fake_repository / "baz/foo.py").read_text()


# REUSE-IgnoreEnd
