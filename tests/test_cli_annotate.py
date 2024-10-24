# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2019 Stefan Bakker <s.bakker777@gmail.com>
# SPDX-FileCopyrightText: 2022 Carmen Bianca Bakker <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2023 Maxim Cournoyer <maxim.cournoyer@gmail.com>
# SPDX-FileCopyrightText: 2024 Rivos Inc.
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for annotate."""

import stat
from inspect import cleandoc
from pathlib import PurePath

import pytest
from click.testing import CliRunner

from reuse.cli.main import main
from reuse.copyright import _COPYRIGHT_PREFIXES

# pylint: disable=too-many-public-methods,too-many-lines,unused-argument


# REUSE-IgnoreStart


class TestAnnotate:
    """Tests for annotate."""

    # TODO: Replace this test with a monkeypatched test
    def test_simple(self, fake_repository, mock_date_today):
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

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "foo.py",
            ],
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == expected

    def test_simple_scheme(self, fake_repository, mock_date_today):
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

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "foo.scm",
            ],
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == expected

    def test_scheme_standardised(self, fake_repository, mock_date_today):
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

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "foo.scm",
            ],
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == expected

    def test_scheme_standardised2(self, fake_repository, mock_date_today):
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

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "foo.scm",
            ],
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == expected

    def test_directory_argument(self, fake_repository):
        """Directory arguments are ignored."""
        result = CliRunner().invoke(
            main, ["annotate", "--copyright", "Jane Doe", "src"]
        )

        assert result.exit_code == 0
        assert result.output == ""
        assert (fake_repository / "src").is_dir()

    def test_simple_no_replace(self, fake_repository, mock_date_today):
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

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--no-replace",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "foo.py",
            ],
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == expected

    def test_year(self, fake_repository):
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

        result = CliRunner().invoke(
            main,
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
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == expected

    def test_no_year(self, fake_repository):
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

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--exclude-year",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "foo.py",
            ],
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == expected

    @pytest.mark.parametrize(
        "copyright_prefix", ["--copyright-prefix", "--copyright-style"]
    )
    def test_copyright_prefix(
        self, fake_repository, copyright_prefix, mock_date_today
    ):
        """Add a header with a specific copyright prefix. Also test the old name
        of the parameter.
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

        result = CliRunner().invoke(
            main,
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
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == expected

    def test_shebang(self, fake_repository):
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

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "foo.py",
            ],
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == expected

    def test_shebang_wrong_comment_style(self, fake_repository):
        """If a comment style does not support the shebang at the top, don't
        treat the shebang as special.
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

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "foo.html",
            ],
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == expected

    def test_contributors_only(
        self, fake_repository, mock_date_today, contributors
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

        result = CliRunner().invoke(
            main,
            args,
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == expected

    def test_contributors(self, fake_repository, mock_date_today, contributors):
        """Add a header with contributor information."""
        simple_file = fake_repository / "foo.py"
        simple_file.write_text("pass")
        content = ["# SPDX-FileCopyrightText: 2018 Jane Doe"]

        if contributors:
            for contributor in sorted(contributors):
                content.append(f"# SPDX-FileContributor: {contributor}")

        content += [
            "#",
            "# SPDX-License-Identifier: GPL-3.0-or-later",
            "",
            "pass",
        ]
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

        result = CliRunner().invoke(
            main,
            args,
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == expected

    def test_specify_style(self, fake_repository, mock_date_today):
        """Add header to a file that does not have one, using a custom style."""
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

        result = CliRunner().invoke(
            main,
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
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == expected

    def test_specify_style_unrecognised(self, fake_repository, mock_date_today):
        """Add a header to a file that is unrecognised."""

        simple_file = fake_repository / "hello.foo"
        simple_file.touch()
        expected = "# SPDX-FileCopyrightText: 2018 Jane Doe"

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--copyright",
                "Jane Doe",
                "--style",
                "python",
                "hello.foo",
            ],
        )

        assert result.exit_code == 0
        assert simple_file.read_text().strip() == expected

    def test_implicit_style(self, fake_repository, mock_date_today):
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

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "foo.js",
            ],
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == expected

    def test_implicit_style_filename(self, fake_repository, mock_date_today):
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

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "Makefile",
            ],
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == expected

    def test_unrecognised_style(self, fake_repository):
        """Add a header to a file that has an unrecognised extension."""
        simple_file = fake_repository / "foo.foo"
        simple_file.write_text("pass")

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "foo.foo",
            ],
        )

        assert result.exit_code != 0
        assert (
            "The following files do not have a recognised file extension"
            in result.output
        )
        assert "foo.foo" in result.output

    @pytest.mark.parametrize(
        "skip_unrecognised", ["--skip-unrecognised", "--skip-unrecognized"]
    )
    def test_skip_unrecognised(self, fake_repository, skip_unrecognised):
        """Skip file that has an unrecognised extension."""
        simple_file = fake_repository / "foo.foo"
        simple_file.write_text("pass")

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                skip_unrecognised,
                "foo.foo",
            ],
        )

        assert result.exit_code == 0
        assert "Skipped unrecognised file 'foo.foo'" in result.output

    @pytest.mark.parametrize(
        "skip_unrecognised", ["--skip-unrecognised", "--skip-unrecognized"]
    )
    def test_skip_unrecognised_and_style_mutex(
        self, fake_repository, skip_unrecognised
    ):
        """--skip-unrecognised and --style are mutually exclusive."""
        simple_file = fake_repository / "foo.foo"
        simple_file.write_text("pass")

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "--style=c",
                skip_unrecognised,
                "foo.foo",
            ],
        )

        assert result.exit_code != 0
        assert "mutually exclusive with" in result.output

    def test_no_data_to_add(self, fake_repository):
        """Add a header, but supply no copyright, license, or contributor."""
        simple_file = fake_repository / "foo.py"
        simple_file.write_text("pass")

        result = CliRunner().invoke(main, ["annotate", "foo.py"])

        assert result.exit_code != 0
        assert (
            "Option '--copyright', '--license', or '--contributor' is required"
            in result.output
        )

    def test_template_simple(
        self, fake_repository, mock_date_today, template_simple_source
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

        result = CliRunner().invoke(
            main,
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
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == expected

    def test_template_simple_multiple(
        self, fake_repository, mock_date_today, template_simple_source
    ):
        """Add a header with a custom template to multiple files."""
        simple_files = [fake_repository / f"foo{i}.py" for i in range(10)]
        for simple_file in simple_files:
            simple_file.write_text("pass")
        template_file = fake_repository / ".reuse/templates/mytemplate.jinja2"
        template_file.parent.mkdir(parents=True, exist_ok=True)
        template_file.write_text(template_simple_source)

        result = CliRunner().invoke(
            main,
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
        )

        assert result.exit_code == 0
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

    def test_template_no_spdx(self, fake_repository, template_no_spdx_source):
        """Add a header with a template that lacks REUSE info."""
        simple_file = fake_repository / "foo.py"
        simple_file.write_text("pass")
        template_file = fake_repository / ".reuse/templates/mytemplate.jinja2"
        template_file.parent.mkdir(parents=True, exist_ok=True)
        template_file.write_text(template_no_spdx_source)

        result = CliRunner().invoke(
            main,
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
        )

        assert result.exit_code == 1

    def test_template_commented(
        self, fake_repository, mock_date_today, template_commented_source
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

        result = CliRunner().invoke(
            main,
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
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == expected

    def test_template_nonexistant(self, fake_repository):
        """Raise an error when using a header that does not exist."""

        simple_file = fake_repository / "foo.py"
        simple_file.write_text("pass")

        result = CliRunner().invoke(
            main,
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
        )

        assert result.exit_code != 0
        assert (
            "Template 'mytemplate.jinja2' could not be found" in result.output
        )

    def test_template_without_extension(
        self, fake_repository, mock_date_today, template_simple_source
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

        result = CliRunner().invoke(
            main,
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
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == expected

    def test_binary(self, fake_repository, mock_date_today, binary_string):
        """Add a header to a .license file if the file is a binary."""
        binary_file = fake_repository / "foo.png"
        binary_file.write_bytes(binary_string)
        expected = cleandoc(
            """
            SPDX-FileCopyrightText: 2018 Jane Doe

            SPDX-License-Identifier: GPL-3.0-or-later
            """
        )

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "foo.png",
            ],
        )

        assert result.exit_code == 0
        assert (
            binary_file.with_name(f"{binary_file.name}.license")
            .read_text()
            .strip()
            == expected
        )

    def test_uncommentable_json(self, fake_repository, mock_date_today):
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

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "foo.json",
            ],
        )

        assert result.exit_code == 0
        assert (
            json_file.with_name(f"{json_file.name}.license").read_text().strip()
            == expected
        )

    def test_fallback_dot_license(self, fake_repository, mock_date_today):
        """Add a header to .license if --fallback-dot-license is given, and no
        style yet exists.
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

        result = CliRunner().invoke(
            main,
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
        )

        assert result.exit_code == 0
        assert expected_py in (fake_repository / "foo.py").read_text()
        assert (fake_repository / "foo.foo.license").exists()
        assert (
            fake_repository / "foo.foo.license"
        ).read_text().strip() == expected_foo
        assert (
            "'foo.foo' is not recognised; creating 'foo.foo.license'"
            in result.output
        )

    def test_force_dot_license(self, fake_repository, mock_date_today):
        """Add a header to a .license file if --force-dot-license is given."""
        simple_file = fake_repository / "foo.py"
        simple_file.write_text("pass")
        expected = cleandoc(
            """
            SPDX-FileCopyrightText: 2018 Jane Doe

            SPDX-License-Identifier: GPL-3.0-or-later
            """
        )

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "--force-dot-license",
                "foo.py",
            ],
        )

        assert result.exit_code == 0
        assert (
            simple_file.with_name(f"{simple_file.name}.license")
            .read_text()
            .strip()
            == expected
        )
        assert simple_file.read_text() == "pass"

    def test_force_dot_license_double(self, fake_repository, mock_date_today):
        """If path.license already exists, don't create path.license.license."""
        simple_file = fake_repository / "foo.txt"
        simple_file_license = fake_repository / "foo.txt.license"
        simple_file_license_license = (
            fake_repository / "foo.txt.license.license"
        )

        simple_file.write_text("foo")
        simple_file_license.write_text("foo")
        expected = cleandoc(
            """
            SPDX-FileCopyrightText: 2018 Jane Doe

            SPDX-License-Identifier: GPL-3.0-or-later
            """
        )

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "--force-dot-license",
                "foo.txt",
            ],
        )

        assert result.exit_code == 0
        assert not simple_file_license_license.exists()
        assert simple_file_license.read_text().strip() == expected

    def test_force_dot_license_unsupported_filetype(
        self, fake_repository, mock_date_today
    ):
        """Add a header to a .license file if --force-dot-license is given, with
        the base file being an otherwise unsupported filetype.
        """
        simple_file = fake_repository / "foo.txt"
        simple_file.write_text("Preserve this")
        expected = cleandoc(
            """
            SPDX-FileCopyrightText: 2018 Jane Doe

            SPDX-License-Identifier: GPL-3.0-or-later
            """
        )

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "--force-dot-license",
                "foo.txt",
            ],
        )

        assert result.exit_code == 0
        assert (
            simple_file.with_name(f"{simple_file.name}.license")
            .read_text()
            .strip()
            == expected
        )
        assert simple_file.read_text() == "Preserve this"

    def test_to_read_only_file_forbidden(
        self, fake_repository, mock_date_today
    ):
        """Cannot add a header without having write permission."""
        _file = fake_repository / "test.sh"
        _file.write_text("#!/bin/sh")
        _file.chmod(mode=stat.S_IREAD)
        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "Apache-2.0",
                "--copyright",
                "mycorp",
                "--style",
                "python",
                "test.sh",
            ],
        )

        assert result.exit_code != 0
        assert "'test.sh' is not writable." in result.output

    def test_license_file(self, fake_repository, mock_date_today):
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

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "foo.py",
            ],
        )

        assert result.exit_code == 0
        assert license_file.read_text() == expected
        assert simple_file.read_text() == "foo"

    def test_license_file_only_one_newline(
        self, fake_repository, mock_date_today
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

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "foo.py",
            ],
        )

        assert result.exit_code == 0
        assert license_file.read_text() == expected
        assert simple_file.read_text() == "foo"

    def test_year_mutually_exclusive(self, fake_repository):
        """--exclude-year and --year are mutually exclusive."""
        result = CliRunner().invoke(
            main,
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
            ],
        )

        assert result.exit_code != 0
        assert "is mutually exclusive with" in result.output

    def test_single_multi_line_mutually_exclusive(self, fake_repository):
        """--single-line and --multi-line are mutually exclusive."""
        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "--single-line",
                "--multi-line",
                "src/source_code.c",
            ],
        )

        assert result.exit_code != 0
        assert "is mutually exclusive with" in result.output

    def test_skip_force_mutually_exclusive(self, fake_repository):
        """--skip-unrecognised and --force-dot-license are mutually exclusive"""
        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "--force-dot-license",
                "--skip-unrecognised",
                "src/source_code.py",
            ],
        )

        assert result.exit_code != 0
        assert "is mutually exclusive with" in result.output

    def test_multi_line_not_supported(self, fake_repository):
        """Expect a fail if --multi-line is not supported for a file type."""
        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "--multi-line",
                "src/source_code.py",
            ],
        )

        assert result.exit_code != 0
        assert (
            "'src/source_code.py' does not support multi-line comments"
            in result.output
        )

    def test_multi_line_not_supported_custom_style(self, fake_repository):
        """--multi-line also fails when used with a style that doesn't support
        it through --style.
        """
        (fake_repository / "foo.foo").write_text("foo")
        result = CliRunner().invoke(
            main,
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

        assert result.exit_code != 0
        assert "'foo.foo' does not support multi-line" in result.output

    def test_single_line_not_supported(self, fake_repository):
        """Expect a fail if --single-line is not supported for a file type."""
        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "--single-line",
                "src/source_code.html",
            ],
        )

        assert result.exit_code != 0
        assert (
            "'src/source_code.html' does not support single-line comments"
            in result.output
        )

    def test_force_multi_line_for_c(self, fake_repository, mock_date_today):
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

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "--multi-line",
                "foo.c",
            ],
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == expected

    @pytest.mark.parametrize("line_ending", ["\r\n", "\r", "\n"])
    def test_line_endings(self, empty_directory, mock_date_today, line_ending):
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

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "foo.py",
            ],
        )

        assert result.exit_code == 0
        with open(simple_file, newline="", encoding="utf-8") as fp:
            contents = fp.read()

        assert contents == expected

    def test_skip_existing(self, fake_repository, mock_date_today):
        """When annotate --skip-existing on a file that already contains REUSE
        info, don't write additional information to it.
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

        CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Jane Doe",
                "foo.py",
            ],
        )

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "MIT",
                "--copyright",
                "John Doe",
                "--skip-existing",
                "foo.py",
                "bar.py",
            ],
        )

        assert result.exit_code == 0
        assert (fake_repository / "foo.py").read_text() == expected_foo
        assert (fake_repository / "bar.py").read_text() == expected_bar

    def test_recursive(self, fake_repository, mock_date_today):
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

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--copyright",
                "Joe Somebody",
                "--recursive",
                "src/",
            ],
        )

        for path in (fake_repository / "src").rglob("src/**"):
            content = path.read_text()
            assert "SPDX-FileCopyrightText: 2018 Joe Somebody" in content

        assert (
            "Joe Somebody" not in (fake_repository / "bar/bar.py").read_text()
        )
        assert result.exit_code == 0

    def test_recursive_on_file(self, fake_repository, mock_date_today):
        """Don't expect errors when annotate is run 'recursively' on a file."""
        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--copyright",
                "Joe Somebody",
                "--recursive",
                "src/source_code.py",
            ],
        )

        assert (
            "Joe Somebody"
            in (fake_repository / "src/source_code.py").read_text()
        )
        assert result.exit_code == 0

    def test_exit_if_unrecognised(self, fake_repository, mock_date_today):
        """Expect error and no edited files if at least one file has not been
        recognised, with --exit-if-unrecognised enabled."""
        (fake_repository / "baz").mkdir(parents=True)
        (fake_repository / "baz/foo.py").write_text("foo")
        (fake_repository / "baz/bar.unknown").write_text("bar")
        (fake_repository / "baz/baz.sh").write_text("baz")

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--license",
                "Apache-2.0",
                "--copyright",
                "Jane Doe",
                "--recursive",
                "baz/",
            ],
        )

        assert result.exit_code != 0
        assert (
            "The following files do not have a recognised file extension"
            in result.output
        )
        assert str(PurePath("baz/bar.unknown")) in result.output
        assert "foo.py" not in result.output
        assert "Jane Doe" not in (fake_repository / "baz/foo.py").read_text()


class TestAnnotateMerge:
    """Test merging copyright statements."""

    def test_simple(self, fake_repository):
        """Add multiple headers to a file with merge copyrights."""
        simple_file = fake_repository / "foo.py"
        simple_file.write_text("pass")

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--year",
                "2016",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Mary Sue",
                "--merge-copyrights",
                "foo.py",
            ],
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == cleandoc(
            """
                # SPDX-FileCopyrightText: 2016 Mary Sue
                #
                # SPDX-License-Identifier: GPL-3.0-or-later

                pass
                """
        )

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--year",
                "2018",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Mary Sue",
                "--merge-copyrights",
                "foo.py",
            ],
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == cleandoc(
            """
                # SPDX-FileCopyrightText: 2016 - 2018 Mary Sue
                #
                # SPDX-License-Identifier: GPL-3.0-or-later

                pass
                """
        )

    def test_multi_prefix(self, fake_repository):
        """Add multiple headers to a file with merge copyrights."""
        simple_file = fake_repository / "foo.py"
        simple_file.write_text("pass")

        for i in range(0, 3):
            result = CliRunner().invoke(
                main,
                [
                    "annotate",
                    "--year",
                    str(2010 + i),
                    "--license",
                    "GPL-3.0-or-later",
                    "--copyright",
                    "Mary Sue",
                    "foo.py",
                ],
            )

            assert result.exit_code == 0

        for i in range(0, 5):
            result = CliRunner().invoke(
                main,
                [
                    "annotate",
                    "--year",
                    str(2015 + i),
                    "--license",
                    "GPL-3.0-or-later",
                    "--copyright-prefix",
                    "string-c",
                    "--copyright",
                    "Mary Sue",
                    "foo.py",
                ],
            )

            assert result.exit_code == 0

        assert simple_file.read_text() == cleandoc(
            """
                # Copyright (C) 2015 Mary Sue
                # Copyright (C) 2016 Mary Sue
                # Copyright (C) 2017 Mary Sue
                # Copyright (C) 2018 Mary Sue
                # Copyright (C) 2019 Mary Sue
                # SPDX-FileCopyrightText: 2010 Mary Sue
                # SPDX-FileCopyrightText: 2011 Mary Sue
                # SPDX-FileCopyrightText: 2012 Mary Sue
                #
                # SPDX-License-Identifier: GPL-3.0-or-later

                pass
                """
        )

        result = CliRunner().invoke(
            main,
            [
                "annotate",
                "--year",
                "2018",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Mary Sue",
                "--merge-copyrights",
                "foo.py",
            ],
        )

        assert result.exit_code == 0
        assert simple_file.read_text() == cleandoc(
            """
                # Copyright (C) 2010 - 2019 Mary Sue
                #
                # SPDX-License-Identifier: GPL-3.0-or-later

                pass
                """
        )

    def test_no_year_in_existing(self, fake_repository, mock_date_today):
        """This checks the issue reported in
        <https://github.com/fsfe/reuse-tool/issues/866>. If an existing
        copyright line doesn't have a year, everything should still work.
        """
        (fake_repository / "foo.py").write_text(
            cleandoc(
                """
                # SPDX-FileCopyrightText: Jane Doe
                """
            )
        )
        CliRunner().invoke(
            main,
            [
                "annotate",
                "--merge-copyrights",
                "--copyright",
                "John Doe",
                "foo.py",
            ],
        )
        assert (
            cleandoc(
                """
                # SPDX-FileCopyrightText: 2018 John Doe
                # SPDX-FileCopyrightText: Jane Doe
                """
            )
            in (fake_repository / "foo.py").read_text()
        )

    def test_all_prefixes(self, fake_repository, mock_date_today):
        """Test that merging works for all copyright prefixes."""
        # TODO: there should probably also be a test for mixing copyright
        # prefixes, but this behaviour is really unpredictable to me at the
        # moment, and the whole copyright-line-as-string thing needs
        # overhauling.
        simple_file = fake_repository / "foo.py"
        for copyright_prefix, copyright_string in _COPYRIGHT_PREFIXES.items():
            simple_file.write_text("pass")
            result = CliRunner().invoke(
                main,
                [
                    "annotate",
                    "--year",
                    "2016",
                    "--license",
                    "GPL-3.0-or-later",
                    "--copyright",
                    "Jane Doe",
                    "--copyright-style",
                    copyright_prefix,
                    "--merge-copyrights",
                    "foo.py",
                ],
            )
            assert result.exit_code == 0
            assert simple_file.read_text(encoding="utf-8") == cleandoc(
                f"""
                    # {copyright_string} 2016 Jane Doe
                    #
                    # SPDX-License-Identifier: GPL-3.0-or-later

                    pass
                    """
            )

            result = CliRunner().invoke(
                main,
                [
                    "annotate",
                    "--year",
                    "2018",
                    "--license",
                    "GPL-3.0-or-later",
                    "--copyright",
                    "Jane Doe",
                    "--copyright-style",
                    copyright_prefix,
                    "--merge-copyrights",
                    "foo.py",
                ],
            )
            assert result.exit_code == 0
            assert simple_file.read_text(encoding="utf-8") == cleandoc(
                f"""
                    # {copyright_string} 2016 - 2018 Jane Doe
                    #
                    # SPDX-License-Identifier: GPL-3.0-or-later

                    pass
                    """
            )


# REUSE-IgnoreEnd
