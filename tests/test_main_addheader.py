# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2019 Stefan Bakker <s.bakker777@gmail.com>
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse._main: addheader"""

# pylint: disable=unused-argument

from inspect import cleandoc

import pytest

from reuse._main import main


# TODO: Replace this test with a monkeypatched test
def test_addheader_simple(fake_repository, stringio, mock_date_today):
    """Add a header to a file that does not have one."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")

    result = main(
        [
            "addheader",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        simple_file.read_text()
        == cleandoc(
            """
            # spdx-FileCopyrightText: 2018 Mary Sue
            #
            # spdx-License-Identifier: GPL-3.0-or-later

            pass
            """
        ).replace("spdx", "SPDX")
    )


def test_addheader_year(fake_repository, stringio):
    """Add a header to a file with a custom year."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")

    result = main(
        [
            "addheader",
            "--year",
            "2016",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        simple_file.read_text()
        == cleandoc(
            """
            # spdx-FileCopyrightText: 2016 Mary Sue
            #
            # spdx-License-Identifier: GPL-3.0-or-later

            pass
            """
        ).replace("spdx", "SPDX")
    )


def test_addheader_no_year(fake_repository, stringio):
    """Add a header to a file without a year."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")

    result = main(
        [
            "addheader",
            "--exclude-year",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        simple_file.read_text()
        == cleandoc(
            """
            # spdx-FileCopyrightText: Mary Sue
            #
            # spdx-License-Identifier: GPL-3.0-or-later

            pass
            """
        ).replace("spdx", "SPDX")
    )


def test_addheader_specify_style(fake_repository, stringio, mock_date_today):
    """Add a header to a file that does not have one, using a custom style."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")

    result = main(
        [
            "addheader",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "--style",
            "c",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        simple_file.read_text()
        == cleandoc(
            """
            // spdx-FileCopyrightText: 2018 Mary Sue
            //
            // spdx-License-Identifier: GPL-3.0-or-later

            pass
            """
        ).replace("spdx", "SPDX")
    )


def test_addheader_implicit_style(fake_repository, stringio, mock_date_today):
    """Add a header to a file that has a recognised extension."""
    simple_file = fake_repository / "foo.js"
    simple_file.write_text("pass")

    result = main(
        [
            "addheader",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "foo.js",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        simple_file.read_text()
        == cleandoc(
            """
            // spdx-FileCopyrightText: 2018 Mary Sue
            //
            // spdx-License-Identifier: GPL-3.0-or-later

            pass
            """
        ).replace("spdx", "SPDX")
    )


def test_addheader_implicit_style_filename(
    fake_repository, stringio, mock_date_today
):
    """Add a header to a filename that is recognised."""
    simple_file = fake_repository / "Makefile"
    simple_file.write_text("pass")

    result = main(
        [
            "addheader",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "Makefile",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        simple_file.read_text()
        == cleandoc(
            """
            # spdx-FileCopyrightText: 2018 Mary Sue
            #
            # spdx-License-Identifier: GPL-3.0-or-later

            pass
            """
        ).replace("spdx", "SPDX")
    )


def test_addheader_unrecognised_style(fake_repository):
    """Add a header to a file that has an unrecognised extension."""
    simple_file = fake_repository / "foo.foo"
    simple_file.write_text("pass")

    with pytest.raises(SystemExit):
        main(
            [
                "addheader",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Mary Sue",
                "foo.foo",
            ]
        )


def test_addheader_skip_unrecognised(fake_repository, stringio):
    """Skip file that has an unrecognised extension."""
    simple_file = fake_repository / "foo.foo"
    simple_file.write_text("pass")

    result = main(
        [
            "addheader",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "--skip-unrecognised",
            "foo.foo",
        ],
        out=stringio,
    )

    assert result == 0
    assert "Skipped unrecognised file foo.foo" in stringio.getvalue()


def test_addheader_skip_unrecognised_and_style(
    fake_repository, stringio, caplog
):
    """--skip-unrecognised and --style show warning message."""
    simple_file = fake_repository / "foo.foo"
    simple_file.write_text("pass")

    result = main(
        [
            "addheader",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "--style=c",
            "--skip-unrecognised",
            "foo.foo",
        ],
        out=stringio,
    )

    assert result == 0
    assert "no effect" in caplog.text


def test_addheader_no_copyright_or_license(fake_repository):
    """Add a header, but supply no copyright or license."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")

    with pytest.raises(SystemExit):
        main(["addheader", "foo.py"])


def test_addheader_template_simple(
    fake_repository, stringio, mock_date_today, template_simple_source
):
    """Add a header with a custom template."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")
    template_file = fake_repository / ".reuse/templates/mytemplate.jinja2"
    template_file.parent.mkdir(parents=True, exist_ok=True)
    template_file.write_text(template_simple_source)

    result = main(
        [
            "addheader",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "--template",
            "mytemplate.jinja2",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        simple_file.read_text()
        == cleandoc(
            """
            # Hello, world!
            #
            # spdx-FileCopyrightText: 2018 Mary Sue
            #
            # spdx-License-Identifier: GPL-3.0-or-later

            pass
            """
        ).replace("spdx", "SPDX")
    )


def test_addheader_template_simple_multiple(
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
            "addheader",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "--template",
            "mytemplate.jinja2",
        ]
        + list(map(str, simple_files)),
        out=stringio,
    )

    assert result == 0
    for simple_file in simple_files:
        assert (
            simple_file.read_text()
            == cleandoc(
                """
                # Hello, world!
                #
                # spdx-FileCopyrightText: 2018 Mary Sue
                #
                # spdx-License-Identifier: GPL-3.0-or-later

                pass
                """
            ).replace("spdx", "SPDX")
        )


def test_addheader_template_no_spdx(
    fake_repository, stringio, template_no_spdx_source
):
    """Add a header with a template that lacks SPDX info."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")
    template_file = fake_repository / ".reuse/templates/mytemplate.jinja2"
    template_file.parent.mkdir(parents=True, exist_ok=True)
    template_file.write_text(template_no_spdx_source)

    result = main(
        [
            "addheader",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "--template",
            "mytemplate.jinja2",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 1


def test_addheader_template_commented(
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

    result = main(
        [
            "addheader",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "--template",
            "mytemplate.commented.jinja2",
            "foo.c",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        simple_file.read_text()
        == cleandoc(
            """
            # Hello, world!
            #
            # spdx-FileCopyrightText: 2018 Mary Sue
            #
            # spdx-License-Identifier: GPL-3.0-or-later

            pass
            """
        ).replace("spdx", "SPDX")
    )


def test_addheader_template_nonexistant(fake_repository):
    """Raise an error when using a header that does not exist."""

    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")

    with pytest.raises(SystemExit):
        main(
            [
                "addheader",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Mary Sue",
                "--template",
                "mytemplate.jinja2",
                "foo.py",
            ]
        )


def test_addheader_template_without_extension(
    fake_repository, stringio, mock_date_today, template_simple_source
):

    """Find the correct header even when not using an extension."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")
    template_file = fake_repository / ".reuse/templates/mytemplate.jinja2"
    template_file.parent.mkdir(parents=True, exist_ok=True)
    template_file.write_text(template_simple_source)

    result = main(
        [
            "addheader",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "--template",
            "mytemplate",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        simple_file.read_text()
        == cleandoc(
            """
            # Hello, world!
            #
            # spdx-FileCopyrightText: 2018 Mary Sue
            #
            # spdx-License-Identifier: GPL-3.0-or-later

            pass
            """
        ).replace("spdx", "SPDX")
    )


def test_addheader_binary(
    fake_repository, stringio, mock_date_today, binary_string
):
    """Add a header to a .license file if the file is a binary."""
    binary_file = fake_repository / "foo.png"
    binary_file.write_bytes(binary_string)

    result = main(
        [
            "addheader",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "foo.png",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        binary_file.with_name(f"{binary_file.name}.license")
        .read_text()
        .strip()
        == cleandoc(
            """
            spdx-FileCopyrightText: 2018 Mary Sue

            spdx-License-Identifier: GPL-3.0-or-later
            """
        ).replace("spdx", "SPDX")
    )


def test_addheader_explicit_license(
    fake_repository, stringio, mock_date_today
):
    """Add a header to a .license file if --explicit-license is given."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")

    result = main(
        [
            "addheader",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "--explicit-license",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        simple_file.with_name(f"{simple_file.name}.license")
        .read_text()
        .strip()
        == cleandoc(
            """
            spdx-FileCopyrightText: 2018 Mary Sue

            spdx-License-Identifier: GPL-3.0-or-later
            """
        ).replace("spdx", "SPDX")
    )
    assert simple_file.read_text() == "pass"


def test_addheader_explicit_license_double(
    fake_repository, stringio, mock_date_today
):
    """When path.license already exists, don't create path.license.license."""
    simple_file = fake_repository / "foo.txt"
    simple_file_license = fake_repository / "foo.txt.license"
    simple_file_license_license = fake_repository / "foo.txt.license.license"

    simple_file.write_text("foo")
    simple_file_license.write_text("foo")

    result = main(
        [
            "addheader",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "--explicit-license",
            "foo.txt",
        ],
        out=stringio,
    )

    assert result == 0
    assert not simple_file_license_license.exists()
    assert (
        simple_file_license.read_text().strip()
        == cleandoc(
            """
            spdx-FileCopyrightText: 2018 Mary Sue

            spdx-License-Identifier: GPL-3.0-or-later
            """
        ).replace("spdx", "SPDX")
    )


def test_addheader_explicit_license_unsupported_filetype(
    fake_repository, stringio, mock_date_today
):
    """Add a header to a .license file if --explicit-license is given, with the
    base file being an otherwise unsupported filetype.
    """
    simple_file = fake_repository / "foo.txt"
    simple_file.write_text("Preserve this")

    result = main(
        [
            "addheader",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "--explicit-license",
            "foo.txt",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        simple_file.with_name(f"{simple_file.name}.license")
        .read_text()
        .strip()
        == cleandoc(
            """
            spdx-FileCopyrightText: 2018 Mary Sue

            spdx-License-Identifier: GPL-3.0-or-later
            """
        ).replace("spdx", "SPDX")
    )
    assert simple_file.read_text() == "Preserve this"


def test_addheader_license_file(fake_repository, stringio, mock_date_today):
    """Add a header to a .license file if it exists."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("foo")
    license_file = fake_repository / "foo.py.license"
    license_file.write_text(
        cleandoc(
            """
            spdx-FileCopyrightText: 2016 Jane Doe

            Hello
            """
        ).replace("spdx", "SPDX")
    )

    result = main(
        [
            "addheader",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        license_file.read_text()
        == cleandoc(
            """
            spdx-FileCopyrightText: 2016 Jane Doe
            spdx-FileCopyrightText: 2018 Mary Sue

            spdx-License-Identifier: GPL-3.0-or-later
            """
        ).replace("spdx", "SPDX")
    )
    assert simple_file.read_text() == "foo"


def test_addheader_year_mutually_exclusive(fake_repository):
    """--exclude-year and --year are mutually exclusive."""
    with pytest.raises(SystemExit):
        main(
            [
                "addheader",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Mary Sue",
                "--exclude-year",
                "--year",
                "2020",
                "src/source_code.py",
            ]
        )


def test_addheader_single_multi_line_mutually_exclusive(fake_repository):
    """--single-line and --multi-line are mutually exclusive."""
    with pytest.raises(SystemExit):
        main(
            [
                "addheader",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Mary Sue",
                "--single-line",
                "--multi-line",
                "src/source_code.c",
            ]
        )


@pytest.mark.parametrize("skip_option", [("--skip-unrecognised"), ("")])
def test_addheader_multi_line_not_supported(fake_repository, skip_option):
    """Expect a fail if --multi-line is not supported for a file type."""
    with pytest.raises(SystemExit):
        main(
            [
                "addheader",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Mary Sue",
                "--multi-line",
                skip_option,
                "src/source_code.py",
            ]
        )


@pytest.mark.parametrize("skip_option", [("--skip-unrecognised"), ("")])
def test_addheader_single_line_not_supported(fake_repository, skip_option):
    """Expect a fail if --single-line is not supported for a file type."""
    with pytest.raises(SystemExit):
        main(
            [
                "addheader",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Mary Sue",
                "--single-line",
                skip_option,
                "src/source_code.html",
            ]
        )


def test_addheader_force_multi_line_for_c(
    fake_repository, stringio, mock_date_today
):
    """--multi-line forces a multi-line comment for C."""
    simple_file = fake_repository / "foo.c"
    simple_file.write_text("foo")

    result = main(
        [
            "addheader",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "--multi-line",
            "foo.c",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        simple_file.read_text()
        == cleandoc(
            """
            /*
             * spdx-FileCopyrightText: 2018 Mary Sue
             *
             * spdx-License-Identifier: GPL-3.0-or-later
             */

            foo
            """
        ).replace("spdx", "SPDX")
    )
