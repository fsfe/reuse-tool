# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Global fixtures and configuration."""

# pylint: disable=redefined-outer-name,subprocess-run-check

import datetime
import logging
import multiprocessing as mp
import os
import shutil
import subprocess
import sys
from inspect import cleandoc
from io import StringIO
from pathlib import Path
from typing import Optional
from unittest.mock import create_autospec

import pytest
from debian.copyright import Copyright
from jinja2 import Environment

os.environ["LC_ALL"] = "C"

# A trick that tries to import the installed version of reuse. If that doesn't
# work, import from the src directory. If that also doesn't work (for some
# reason), then an ImportError is raised.
try:
    # pylint: disable=unused-import
    import reuse
except ImportError:
    sys.path.append(os.path.join(Path(__file__).parent.parent, "src"))
finally:
    from reuse._util import GIT_EXE, HG_EXE, setup_logging

CWD = Path.cwd()

TESTS_DIRECTORY = Path(__file__).parent.resolve()
RESOURCES_DIRECTORY = TESTS_DIRECTORY / "resources"


def pytest_configure():
    """Called after command line options have been parsed and all plugins and
    initial conftest files been loaded.
    """
    setup_logging(level=logging.DEBUG)


def pytest_runtest_setup(item):
    """Called before running a test."""
    # pylint: disable=unused-argument
    # Make sure to restore CWD
    os.chdir(CWD)


@pytest.fixture(params=[True, False])
def git_exe(request, monkeypatch) -> Optional[str]:
    """Run the test with or without git."""
    exe = GIT_EXE if request.param else ""
    monkeypatch.setattr("reuse.project.GIT_EXE", exe)
    monkeypatch.setattr("reuse._util.GIT_EXE", exe)
    yield exe


@pytest.fixture(params=[True, False])
def hg_exe(request, monkeypatch) -> Optional[str]:
    """Run the test with or without mercurial (hg)."""
    exe = HG_EXE if request.param else ""
    monkeypatch.setattr("reuse.project.HG_EXE", exe)
    monkeypatch.setattr("reuse._util.HG_EXE", exe)
    yield exe


@pytest.fixture(params=[True, False])
def multiprocessing(request, monkeypatch) -> bool:
    """Run the test with or without multiprocessing."""
    if not request.param:
        monkeypatch.delattr(mp, "Pool")
    yield request.param


@pytest.fixture()
def empty_directory(tmpdir_factory) -> Path:
    """Create a temporary empty directory."""
    directory = Path(str(tmpdir_factory.mktemp("empty_directory")))

    os.chdir(str(directory))
    return directory


@pytest.fixture()
def fake_repository(tmpdir_factory) -> Path:
    """Create a temporary fake repository."""
    directory = Path(str(tmpdir_factory.mktemp("fake_repository")))
    for file_ in (RESOURCES_DIRECTORY / "fake_repository").iterdir():
        if file_.is_file():
            shutil.copy(file_, directory / file_.name)
        elif file_.is_dir():
            shutil.copytree(file_, directory / file_.name)

    # Get rid of those pesky pyc files.
    shutil.rmtree(directory / "src/__pycache__", ignore_errors=True)

    # Adding this here to avoid conflict in main project.
    (directory / "src/exception.py").write_text(
        "SPDX-FileCopyrightText: 2017 Mary Sue\n"
        "SPDX"
        "-License-Identifier: GPL-3.0-or-later WITH Autoconf-exception-3.0"
    )
    (directory / "src/custom.py").write_text(
        "SPDX-FileCopyrightText: 2017 Mary Sue\n"
        "SPDX"
        "-License-Identifier: LicenseRef-custom"
    )

    os.chdir(directory)
    return directory


def _repo_contents(
    fake_repository, ignore_filename=".gitignore", ignore_prefix=""
):
    """Generate contents for a vcs repository.

    Currently defaults to git-like behavior for ignoring files with
    the expectation that other tools can be configured to ignore files
    by just chanigng the ignore-file-name and enabling git-like behavior
    with a prefix line in the ignore file.
    """
    gitignore = ignore_prefix + (
        "# SPDX"
        "-License-Identifier: CC0-1.0\n"
        "# SPDX"
        "-FileCopyrightText: 2017 Mary Sue\n"
        "*.pyc\nbuild"
    )
    (fake_repository / ignore_filename).write_text(gitignore)
    (fake_repository / "LICENSES/CC0-1.0.txt").write_text("License text")

    for file_ in (fake_repository / "src").iterdir():
        if file_.suffix == ".py":
            file_.with_suffix(".pyc").write_text("foo")

    build_dir = fake_repository / "build"
    build_dir.mkdir()
    (build_dir / "hello.py").write_text("foo")


@pytest.fixture()
def git_repository(fake_repository: Path, git_exe: Optional[str]) -> Path:
    """Create a git repository with ignored files."""
    if not git_exe:
        pytest.skip("cannot run this test without git")

    os.chdir(fake_repository)
    _repo_contents(fake_repository)

    subprocess.run([git_exe, "init", str(fake_repository)])
    subprocess.run([git_exe, "add", str(fake_repository)])
    subprocess.run(
        [
            git_exe,
            "-c",
            "user.name",
            "Example",
            "-c",
            "user.email",
            "example@example.com",
            "commit",
            "-m",
            "initial",
        ]
    )

    return fake_repository


@pytest.fixture()
def hg_repository(fake_repository: Path, hg_exe: Optional[str]) -> Path:
    """Create a mercurial repository with ignored files."""
    if not hg_exe:
        pytest.skip("cannot run this test without mercurial")

    os.chdir(fake_repository)
    _repo_contents(
        fake_repository,
        ignore_filename=".hgignore",
        ignore_prefix="syntax:glob",
    )

    subprocess.run([hg_exe, "init", "."])
    subprocess.run([hg_exe, "addremove"])
    subprocess.run(
        [
            hg_exe,
            "commit",
            "--user",
            "Example <example@example.com>",
            "-m",
            "initial",
        ]
    )

    return fake_repository


@pytest.fixture()
def submodule_repository(
    git_repository: Path, git_exe: Optional[str], tmpdir_factory
) -> Path:
    """Create a git repository that contains a submodule."""
    header = cleandoc(
        """
            spdx-FileCopyrightText: 2019 Jane Doe

            spdx-License-Identifier: CC0-1.0
            """
    ).replace("spdx", "SPDX")

    submodule = Path(str(tmpdir_factory.mktemp("submodule")))
    (submodule / "foo.py").write_text(header)

    os.chdir(submodule)
    subprocess.run([git_exe, "init", str(submodule)])
    subprocess.run([git_exe, "add", str(submodule)])
    subprocess.run(
        [
            git_exe,
            "-c",
            "user.name",
            "Example",
            "-c",
            "user.email",
            "example@example.com",
            "commit",
            "-m",
            "initial",
        ]
    )

    os.chdir(git_repository)
    subprocess.run(
        [git_exe, "submodule", "add", str(submodule.resolve()), "submodule"]
    )
    subprocess.run(
        [
            git_exe,
            "-c",
            "user.name",
            "Example",
            "-c",
            "user.email",
            "example@example.com",
            "commit",
            "-m",
            "add submodule",
        ]
    )

    (git_repository / ".gitmodules.license").write_text(header)

    return git_repository


@pytest.fixture(scope="session")
def copyright():
    """Create a dep5 Copyright object."""
    with (RESOURCES_DIRECTORY / "fake_repository/.reuse/dep5").open() as fp:
        return Copyright(fp)


@pytest.fixture()
def stringio():
    """Create a StringIO object."""
    return StringIO()


@pytest.fixture()
def binary_string():
    """Create a binary string."""
    return bytes(range(256))


@pytest.fixture()
def template_simple_source():
    """Source code of simple Jinja2 template."""
    return cleandoc(
        """
        Hello, world!

        {% for copyright_line in copyright_lines %}
        {{ copyright_line }}
        {% endfor %}

        {% for expression in spdx_expressions %}
        spdx-License-Identifier: {{ expression }}
        {% endfor %}
        """.replace(
            "spdx-Lic", "SPDX-Lic"
        )
    )


@pytest.fixture()
def template_simple(template_simple_source):
    """Provide a simple Jinja2 template."""
    env = Environment(trim_blocks=True)
    return env.from_string(template_simple_source)


@pytest.fixture()
def template_no_spdx_source():
    """Source code of Jinja2 template without SPDX lines."""
    return "Hello, world"


@pytest.fixture()
def template_no_spdx(template_no_spdx_source):
    """Provide a Jinja2 template without SPDX lines."""
    env = Environment(trim_blocks=True)
    return env.from_string(template_no_spdx_source)


@pytest.fixture()
def template_commented_source():
    """Source code of a simple Jinja2 template that is already commented."""
    return cleandoc(
        """
        # Hello, world!
        #
        {% for copyright_line in copyright_lines %}
        # {{ copyright_line }}
        {% endfor %}
        #
        {% for expression in spdx_expressions %}
        # spdx-License-Identifier: {{ expression }}
        {% endfor %}
        """.replace(
            "spdx-Lic", "SPDX-Lic"
        )
    )


@pytest.fixture()
def template_commented(template_commented_source):
    """Provide a Jinja2 template that is already commented."""
    env = Environment(trim_blocks=True)
    return env.from_string(template_commented_source)


@pytest.fixture()
def mock_date_today(monkeypatch):
    """Mock away datetime.date.today to always return 2018."""
    date = create_autospec(datetime.date)
    date.today.return_value = datetime.date(2018, 1, 1)
    monkeypatch.setattr(datetime, "date", date)
