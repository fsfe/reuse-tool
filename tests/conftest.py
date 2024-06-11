# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Carmen Bianca Bakker <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2023 Matthias Riße
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Global fixtures and configuration."""

# pylint: disable=redefined-outer-name,invalid-name

import contextlib
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
from typing import Generator
from unittest.mock import create_autospec

import pytest
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
    from reuse._util import GIT_EXE, HG_EXE, PIJUL_EXE, setup_logging
    from reuse.global_licensing import ReuseDep5

CWD = Path.cwd()

TESTS_DIRECTORY = Path(__file__).parent.resolve()
RESOURCES_DIRECTORY = TESTS_DIRECTORY / "resources"

try:
    import pwd

    is_root = pwd.getpwuid(os.getuid()).pw_name == "root"
    is_posix = True
except ImportError:
    is_root = False
    is_posix = False

cpython = pytest.mark.skipif(
    sys.implementation.name != "cpython", reason="only CPython supported"
)
git = pytest.mark.skipif(not GIT_EXE, reason="requires git")
no_root = pytest.mark.xfail(is_root, reason="fails when user is root")
posix = pytest.mark.skipif(not is_posix, reason="Windows not supported")


# REUSE-IgnoreStart


def pytest_addoption(parser):
    """Allows specification of additional commandline options to parse"""
    parser.addoption("--loglevel", action="store", default="DEBUG")


def pytest_configure(config):
    """Called after command line options have been parsed and all plugins and
    initial conftest files been loaded.
    """
    loglevel = config.getoption("loglevel")
    setup_logging(level=logging.getLevelName(loglevel))


def pytest_runtest_setup(item):
    """Called before running a test."""
    # pylint: disable=unused-argument
    # Make sure to restore CWD
    os.chdir(CWD)

    # TODO: Awful workaround. In `main`, this environment variable is set under
    # certain conditions. This means that all tests that run _after_ that
    # condition is met also have the environment variable set, because the
    # environment had been changed. There should be a better way to scope this.
    with contextlib.suppress(KeyError):
        del os.environ["_SUPPRESS_DEP5_WARNING"]


@pytest.fixture()
def git_exe() -> str:
    """Run the test with git."""
    if not GIT_EXE:
        pytest.skip("cannot run this test without git")
    return str(GIT_EXE)


@pytest.fixture()
def hg_exe() -> str:
    """Run the test with mercurial (hg)."""
    if not HG_EXE:
        pytest.skip("cannot run this test without mercurial")
    return str(HG_EXE)


@pytest.fixture()
def pijul_exe() -> str:
    """Run the test with Pijul."""
    if not PIJUL_EXE:
        pytest.skip("cannot run this test without pijul")
    return str(PIJUL_EXE)


@pytest.fixture(params=[True, False])
def multiprocessing(request, monkeypatch) -> Generator[bool, None, None]:
    """Run the test with or without multiprocessing."""
    if not request.param:
        monkeypatch.delattr(mp, "Pool")
    yield request.param


@pytest.fixture(params=[True, False])
def add_license_concluded(request) -> Generator[bool, None, None]:
    yield request


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
        "SPDX-FileCopyrightText: 2017 Jane Doe\n"
        "SPDX-License-Identifier: GPL-3.0-or-later WITH Autoconf-exception-3.0",
        encoding="utf-8",
    )
    (directory / "src/custom.py").write_text(
        "SPDX-FileCopyrightText: 2017 Jane Doe\n"
        "SPDX-License-Identifier: LicenseRef-custom",
        encoding="utf-8",
    )
    (directory / "src/multiple_licenses.rs").write_text(
        "SPDX-FileCopyrightText: 2022 Jane Doe\n"
        "SPDX-License-Identifier: GPL-3.0-or-later\n"
        "SPDX-License-Identifier: Apache-2.0 OR CC0-1.0"
        " WITH Autoconf-exception-3.0\n",
        encoding="utf-8",
    )

    os.chdir(directory)
    return directory


@pytest.fixture()
def fake_repository_reuse_toml(fake_repository) -> Path:
    """Add REUSE.toml to the fake repo."""
    shutil.copy(
        RESOURCES_DIRECTORY / "REUSE.toml", fake_repository / "REUSE.toml"
    )
    (fake_repository / "doc/index.rst").touch()
    return fake_repository


@pytest.fixture()
def fake_repository_dep5(fake_repository) -> Path:
    """Add .reuse/dep5 to the fake repo."""
    (fake_repository / ".reuse").mkdir(exist_ok=True)
    shutil.copy(RESOURCES_DIRECTORY / "dep5", fake_repository / ".reuse/dep5")
    (fake_repository / "doc/index.rst").touch()
    return fake_repository


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
        "# SPDX-License-Identifier: CC0-1.0\n"
        "# SPDX-FileCopyrightText: 2017 Jane Doe\n"
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
def git_repository(fake_repository: Path, git_exe: str) -> Path:
    """Create a git repository with ignored files."""
    os.chdir(fake_repository)
    _repo_contents(fake_repository)

    # TODO: To speed this up, maybe directly write to '.gitconfig' instead.
    subprocess.run([git_exe, "init", str(fake_repository)], check=True)
    subprocess.run([git_exe, "config", "user.name", "Example"], check=True)
    subprocess.run(
        [git_exe, "config", "user.email", "example@example.com"], check=True
    )
    subprocess.run([git_exe, "config", "commit.gpgSign", "false"], check=True)

    subprocess.run([git_exe, "add", str(fake_repository)], check=True)
    subprocess.run(
        [
            git_exe,
            "commit",
            "-m",
            "initial",
        ],
        check=True,
    )

    return fake_repository


@pytest.fixture()
def hg_repository(fake_repository: Path, hg_exe: str) -> Path:
    """Create a mercurial repository with ignored files."""
    os.chdir(fake_repository)
    _repo_contents(
        fake_repository,
        ignore_filename=".hgignore",
        ignore_prefix="syntax:glob",
    )

    subprocess.run([hg_exe, "init", "."], check=True)
    subprocess.run([hg_exe, "addremove"], check=True)
    subprocess.run(
        [
            hg_exe,
            "commit",
            "--user",
            "Example <example@example.com>",
            "-m",
            "initial",
        ],
        check=True,
    )

    return fake_repository


@pytest.fixture()
def pijul_repository(fake_repository: Path, pijul_exe: str) -> Path:
    """Create a pijul repository with ignored files."""
    os.chdir(fake_repository)
    _repo_contents(
        fake_repository,
        ignore_filename=".ignore",
    )

    subprocess.run([pijul_exe, "init", "."], check=True)
    subprocess.run([pijul_exe, "add", "--recursive", "."], check=True)
    subprocess.run(
        [
            pijul_exe,
            "record",
            "--all",
            "--message",
            "initial",
        ],
        check=True,
    )

    return fake_repository


@pytest.fixture(params=["submodule-add", "manual"])
def submodule_repository(
    git_repository: Path, git_exe: str, tmpdir_factory, request
) -> Path:
    """Create a git repository that contains a submodule."""
    header = cleandoc(
        """
            SPDX-FileCopyrightText: 2019 Jane Doe

            SPDX-License-Identifier: CC0-1.0
            """
    )

    submodule = Path(str(tmpdir_factory.mktemp("submodule")))
    (submodule / "foo.py").write_text(header, encoding="utf-8")

    os.chdir(submodule)

    subprocess.run([git_exe, "init", str(submodule)], check=True)
    subprocess.run([git_exe, "config", "user.name", "Example"], check=True)
    subprocess.run(
        [git_exe, "config", "user.email", "example@example.com"], check=True
    )

    subprocess.run([git_exe, "add", str(submodule)], check=True)
    subprocess.run(
        [
            git_exe,
            "commit",
            "-m",
            "initial",
        ],
        check=True,
    )

    os.chdir(git_repository)

    if request.param == "submodule-add":
        subprocess.run(
            [
                git_exe,
                # https://git-scm.com/docs/git-config#Documentation/git-config.txt-protocolallow
                #
                # This circumvents a bug/behaviour caused by CVE-2022-39253
                # where you cannot use `git submodule add repository path` where
                # repository is a file on the filesystem.
                "-c",
                "protocol.file.allow=always",
                "submodule",
                "add",
                str(submodule.resolve()),
                "submodule",
            ],
            check=True,
        )
    elif request.param == "manual":
        subprocess.run(
            [git_exe, "clone", str(submodule.resolve()), "submodule"],
            check=True,
        )
        with open(
            git_repository / ".gitmodules", mode="a", encoding="utf-8"
        ) as gitmodules_file:
            gitmodules_file.write(
                f"""[submodule "submodule"]
	path = submodule
	url = {submodule.resolve().as_posix()}
"""
            )
        subprocess.run(
            [
                git_exe,
                "add",
                "--no-warn-embedded-repo",
                ".gitmodules",
                "submodule",
            ],
            check=True,
        )

    subprocess.run(
        [git_exe, "commit", "-m", "add submodule"],
        check=True,
    )
    (git_repository / ".gitmodules.license").write_text(header)

    return git_repository


@pytest.fixture(scope="session")
def reuse_dep5():
    """Create a ReuseDep5 object."""
    return ReuseDep5.from_file(RESOURCES_DIRECTORY / "dep5")


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
        SPDX-License-Identifier: {{ expression }}
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
        # SPDX-License-Identifier: {{ expression }}
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


@pytest.fixture(
    params=[[], ["John Doe"], ["John Doe", "Alice Doe"]],
    ids=["None", "John", "John and Alice"],
)
def contributors(request):
    """Provide contributors for SPDX-FileContributor field generation"""
    yield request.param


# REUSE-IgnoreEnd
