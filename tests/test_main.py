# SPDX-Copyright: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All tests for reuse._main"""

import os

from reuse._main import main


def test_lint(
    fake_repository, stringio, git_exe
):  # pylint: disable=unused-argument
    """Run a successful lint. git_exe is there to make sure that the test
    also works if git is note installed.
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


def test_spdx(fake_repository, stringio):
    """Compile to an SPDX document."""
    os.chdir(str(fake_repository))
    result = main(["spdx"], out=stringio)

    # FIXME: This test is rubbish.
    assert result == 0
    assert stringio.getvalue()
