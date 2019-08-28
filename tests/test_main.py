# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V.
# SPDX-FileCopyrightText: 2019 Stefan Bakker <s.bakker777@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All tests for reuse._main"""

# pylint: disable=redefined-outer-name

import datetime
import errno
import os
from inspect import cleandoc
from pathlib import Path
from unittest.mock import create_autospec

import pytest
import requests

from reuse import download
from reuse._main import main


@pytest.fixture()
def mock_put_license_in_file(monkeypatch):
    """Create a mocked version of put_license_in_file."""
    result = create_autospec(download.put_license_in_file)
    monkeypatch.setattr(download, "put_license_in_file", result)
    return result


@pytest.fixture()
def mock_date_today(monkeypatch):
    """Mock away datetime.date.today to always return 2018."""
    date = create_autospec(datetime.date)
    date.today.return_value = datetime.date(2018, 1, 1)
    monkeypatch.setattr(datetime, "date", date)


def test_lint(
    fake_repository, stringio, git_exe
):  # pylint: disable=unused-argument
    """Run a successful lint. git_exe is there to make sure that the test
    also works if git is not installed.
    """
    result = main(["lint", str(fake_repository)], out=stringio)

    assert result == 0
    assert ":-)" in stringio.getvalue()


def test_lint_git(git_repository, stringio):
    """Run a successful lint."""
    result = main(["lint", str(git_repository)], out=stringio)

    assert result == 0
    assert ":-)" in stringio.getvalue()


def test_lint_fail(fake_repository, stringio):
    """Run a failed lint."""
    (fake_repository / "foo.py").touch()
    result = main(["lint", str(fake_repository)], out=stringio)

    assert result > 0
    assert "foo.py" in stringio.getvalue()
    assert ":-(" in stringio.getvalue()


def test_spdx(fake_repository, stringio):
    """Compile to an SPDX document."""
    os.chdir(str(fake_repository))
    result = main(["spdx"], out=stringio)

    # TODO: This test is rubbish.
    assert result == 0
    assert stringio.getvalue()


def test_download(fake_repository, stringio, mock_put_license_in_file):
    """Straightforward test."""
    # pylint: disable=unused-argument
    result = main(["download", "0BSD"], out=stringio)

    assert result == 0
    mock_put_license_in_file.assert_called_with(
        "0BSD", Path("LICENSES/0BSD.txt").resolve()
    )


def test_download_file_exists(
    fake_repository, stringio, mock_put_license_in_file
):
    """The to-be-downloaded file already exists."""
    # pylint: disable=unused-argument
    mock_put_license_in_file.side_effect = FileExistsError(
        errno.EEXIST, "", "GPL-3.0-or-later.txt"
    )

    result = main(["download", "GPL-3.0-or-later"], out=stringio)

    assert result == 1
    assert "GPL-3.0-or-later.txt already exists" in stringio.getvalue()


def test_download_request_exception(
    fake_repository, stringio, mock_put_license_in_file
):
    """There was an error while downloading the license file."""
    # pylint: disable=unused-argument
    mock_put_license_in_file.side_effect = requests.RequestException()

    result = main(["download", "0BSD"], out=stringio)

    assert result == 1
    assert "internet" in stringio.getvalue()


def test_download_invalid_spdx(
    fake_repository, stringio, mock_put_license_in_file
):
    """An invalid SPDX identifier was provided."""
    # pylint: disable=unused-argument
    mock_put_license_in_file.side_effect = requests.RequestException()

    result = main(["download", "does-not-exist"], out=stringio)

    assert result == 1
    assert "not a valid SPDX License Identifier" in stringio.getvalue()


def test_download_custom_output(
    empty_directory, stringio, mock_put_license_in_file
):
    """Download the license into a custom file."""
    # pylint: disable=unused-argument
    result = main(["download", "-o", "foo", "0BSD"], out=stringio)

    assert result == 0
    mock_put_license_in_file.assert_called_with(
        "0BSD", destination=Path("foo")
    )


def test_download_custom_output_too_many(
    empty_directory, stringio, mock_put_license_in_file
):
    """Providing more than one license with a custom output results in an
    error.
    """
    # pylint: disable=unused-argument
    with pytest.raises(SystemExit):
        main(
            ["download", "-o", "foo", "0BSD", "GPL-3.0-or-later"], out=stringio
        )


# TODO: Replace this test with a monkeypatched test
def test_addheader_simple(fake_repository, stringio, mock_date_today):
    """Add a header to a file that does not have one."""
    # pylint: disable=unused-argument
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
    # pylint: disable=unused-argument
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
    # pylint: disable=unused-argument
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
    # pylint: disable=unused-argument
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
    # pylint: disable=unused-argument
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
    # pylint: disable=unused-argument
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
    # pylint: disable=unused-argument
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
    # pylint: disable=unused-argument
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
    # pylint: disable=unused-argument
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
    # pylint: disable=unused-argument
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
    # pylint: disable=unused-argument
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
    # pylint: disable=unused-argument
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


def test_addheader_license_file(fake_repository, stringio, mock_date_today):
    """Add a header to a .license file if it exists."""
    # pylint: disable=unused-argument
    simple_file = fake_repository / "foo.py"
    simple_file.touch()
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
    assert not simple_file.read_text()
