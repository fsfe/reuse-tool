# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Carmen Bianca Bakker <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2023 Matthias Riße
# SPDX-FileCopyrightText: 2024 Skyler Grey <sky@a.starrysky.fyi>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Global fixtures and configuration."""

# pylint: disable=redefined-outer-name,invalid-name

import concurrent.futures
import contextlib
import datetime
import importlib
import logging
import os
import shutil
import subprocess
import sys
from collections.abc import Generator
from inspect import cleandoc
from io import StringIO
from pathlib import Path
from unittest.mock import create_autospec

import pytest
from jinja2 import Environment

os.environ["LC_ALL"] = "C"
os.environ["LANGUAGE"] = ""

# A trick that tries to import the installed version of reuse. If that doesn't
# work, import from the src directory. If that also doesn't work (for some
# reason), then an ImportError is raised.
try:
    # pylint: disable=unused-import
    import reuse
except ImportError:
    sys.path.append(os.path.join(Path(__file__).parent.parent, "src"))
finally:
    from reuse import extract, report
    from reuse._util import setup_logging
    from reuse.global_licensing import ReuseDep5
    from reuse.vcs import GIT_EXE, HG_EXE, JUJUTSU_EXE, PIJUL_EXE

try:
    _chardet = bool(importlib.import_module("chardet"))
except ImportError:
    _chardet = False

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
hg = pytest.mark.skipif(not HG_EXE, reason="requires mercurial")
pijul = pytest.mark.skipif(not PIJUL_EXE, reason="requires pijul")
no_root = pytest.mark.xfail(is_root, reason="fails when user is root")
posix = pytest.mark.skipif(not is_posix, reason="Windows not supported")
chardet = pytest.mark.skipif(not _chardet, reason="chardet is not installed")


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

    # Disable parallelisation during tests.
    report.ENABLE_PARALLEL = False


def pytest_runtest_setup(item):
    """Called before running a test."""
    # pylint: disable=unused-argument
    # TODO: Awful workaround. In `main`, this environment variable is set under
    # certain conditions. This means that all tests that run _after_ that
    # condition is met also have the environment variable set, because the
    # environment had been changed. There should be a better way to scope this.
    with contextlib.suppress(KeyError):
        del os.environ["_SUPPRESS_DEP5_WARNING"]


def pytest_runtest_teardown(item):
    """Called after running a test."""
    # pylint: disable=unused-argument
    # Make sure to restore CWD
    os.chdir(CWD)


@pytest.fixture(scope="session")
def git_exe() -> str:
    """Run the test with git."""
    if not GIT_EXE:
        pytest.skip("cannot run this test without git")
    return str(GIT_EXE)


@pytest.fixture(params=[True, False])
def optional_git_exe(request, monkeypatch) -> Generator[str | None, None, None]:
    """Run the test with or without git."""
    exe = GIT_EXE if request.param else ""
    monkeypatch.setattr("reuse.vcs.GIT_EXE", exe)
    yield exe


@pytest.fixture(scope="session")
def hg_exe() -> str:
    """Run the test with mercurial (hg)."""
    if not HG_EXE:
        pytest.skip("cannot run this test without mercurial")
    return str(HG_EXE)


@pytest.fixture(params=[True, False])
def optional_hg_exe(request, monkeypatch) -> Generator[str | None, None, None]:
    """Run the test with or without mercurial."""
    exe = HG_EXE if request.param else ""
    monkeypatch.setattr("reuse.vcs.HG_EXE", exe)
    yield exe


@pytest.fixture(scope="session")
def jujutsu_exe() -> str:
    """Run the test with Jujutsu."""
    if not JUJUTSU_EXE:
        pytest.skip("cannot run this test without jujutsu")
    return str(JUJUTSU_EXE)


@pytest.fixture(params=[True, False])
def optional_jujutsu_exe(
    request, monkeypatch
) -> Generator[str | None, None, None]:
    """Run the test with or without Jujutsu."""
    exe = JUJUTSU_EXE if request.param else ""
    monkeypatch.setattr("reuse.vcs.JUJUTSU_EXE", exe)
    yield exe


@pytest.fixture(scope="session")
def pijul_exe() -> str:
    """Run the test with Pijul."""
    if not PIJUL_EXE:
        pytest.skip("cannot run this test without pijul")
    return str(PIJUL_EXE)


@pytest.fixture(params=[True, False])
def optional_pijul_exe(
    request, monkeypatch
) -> Generator[str | None, None, None]:
    """Run the test with or without Pijul."""
    exe = PIJUL_EXE if request.param else ""
    monkeypatch.setattr("reuse.vcs.PIJUL_EXE", exe)
    yield exe


@pytest.fixture(params=[True, False])
def multiprocessing(request, monkeypatch) -> Generator[bool, None, None]:
    """Run the test with or without multiprocessing."""
    monkeypatch.setattr("reuse.report.ENABLE_PARALLEL", True)
    if not request.param:
        monkeypatch.delattr(concurrent.futures, "ProcessPoolExecutor")
    yield request.param


@pytest.fixture(params=["magic", "charset_normalizer", "chardet"])
def encoding_module(request, monkeypatch) -> Generator[bool, None, None]:
    """Run the test with or without libmagic."""
    try:
        if request.param == "magic" and not is_posix:
            pytest.skip("Windows not supported")
        module = importlib.import_module(request.param)
        monkeypatch.setattr("reuse.extract._ENCODING_MODULE", module)
        yield request.param
    except ImportError:
        pytest.skip(f"'{request.param}' could not be imported")


@pytest.fixture(params=[True, False])
def add_license_concluded(request) -> Generator[bool, None, None]:
    yield request


@pytest.fixture()
def empty_directory(tmpdir_factory) -> Path:
    """Create a temporary empty directory."""
    directory = Path(str(tmpdir_factory.mktemp("empty_directory")))

    os.chdir(str(directory))
    return directory


@pytest.fixture(scope="session")
def _cached_fake_repository(tmp_path_factory) -> Path:
    """Create a temporary fake repository."""
    directory = tmp_path_factory.mktemp("fake_repository")
    shutil.copytree(
        RESOURCES_DIRECTORY / "fake_repository", directory, dirs_exist_ok=True
    )

    # Get rid of those pesky pyc files.
    shutil.rmtree(directory / "src/__pycache__", ignore_errors=True)

    return directory


@pytest.fixture()
def fake_repository(_cached_fake_repository, tmp_path) -> Path:
    """Create a temporary fake repository."""
    shutil.copytree(_cached_fake_repository, tmp_path, dirs_exist_ok=True)
    os.chdir(tmp_path)
    return tmp_path


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


@pytest.fixture(scope="session")
def _cached_git_repository(
    _cached_fake_repository: Path, tmp_path_factory, git_exe: str
) -> Path:
    """Create a git repository with ignored files."""
    directory = tmp_path_factory.mktemp("cached_git_directory")
    shutil.copytree(_cached_fake_repository, directory, dirs_exist_ok=True)
    os.chdir(directory)
    _repo_contents(directory)

    subprocess.run([git_exe, "init", str(directory)], check=True)
    Path(".git/config").write_text(
        cleandoc(
            """
            [user]
              name = Example
              email = example@example.com
            [commit]
              gpgSign = false
            """
        ),
        encoding="utf-8",
    )
    subprocess.run([git_exe, "add", str(directory)], check=True)
    subprocess.run(
        [
            git_exe,
            "commit",
            "-m",
            "initial",
        ],
        check=True,
    )

    return directory


@pytest.fixture()
def git_repository(_cached_git_repository, tmp_path) -> Path:
    """Create a git repository with ignored files."""
    shutil.copytree(_cached_git_repository, tmp_path, dirs_exist_ok=True)
    os.chdir(tmp_path)
    return tmp_path


@pytest.fixture(scope="session")
def _cached_hg_repository(
    _cached_fake_repository: Path, tmp_path_factory, hg_exe: str
) -> Path:
    """Create a mercurial repository with ignored files."""
    directory = tmp_path_factory.mktemp("cached_hg_repository")
    shutil.copytree(_cached_fake_repository, directory, dirs_exist_ok=True)
    os.chdir(directory)
    _repo_contents(
        directory,
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

    return directory


@pytest.fixture()
def hg_repository(_cached_hg_repository, tmp_path) -> Path:
    """Create a mercurial repository with ignored files."""
    shutil.copytree(_cached_hg_repository, tmp_path, dirs_exist_ok=True)
    os.chdir(tmp_path)
    return tmp_path


@pytest.fixture(scope="session")
def _cached_jujutsu_repository(
    _cached_fake_repository: Path, tmp_path_factory, jujutsu_exe: str
) -> Path:
    """Create a jujutsu repository with ignored files."""
    directory = tmp_path_factory.mktemp("cached_jujutsu_repository")
    shutil.copytree(_cached_fake_repository, directory, dirs_exist_ok=True)
    os.chdir(directory)
    _repo_contents(directory)

    subprocess.run([jujutsu_exe, "git", "init", str(directory)], check=True)

    return directory


@pytest.fixture()
def jujutsu_repository(_cached_jujutsu_repository, tmp_path) -> Path:
    """Create a jujutsu repository with ignored files."""
    shutil.copytree(_cached_jujutsu_repository, tmp_path, dirs_exist_ok=True)
    os.chdir(tmp_path)
    return tmp_path


@pytest.fixture(scope="session")
def _cached_pijul_repository(
    _cached_fake_repository: Path, tmp_path_factory, pijul_exe: str
) -> Path:
    """Create a pijul repository with ignored files."""
    directory = tmp_path_factory.mktemp("cached_pijul_repository")
    shutil.copytree(_cached_fake_repository, directory, dirs_exist_ok=True)
    os.chdir(directory)
    _repo_contents(
        directory,
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

    return directory


@pytest.fixture()
def pijul_repository(_cached_pijul_repository, tmp_path) -> Path:
    """Create a pijul repository with ignored files."""
    shutil.copytree(_cached_pijul_repository, tmp_path, dirs_exist_ok=True)
    os.chdir(tmp_path)
    return tmp_path


@pytest.fixture(scope="session", params=["submodule-add", "manual"])
def _cached_submodule_repository(
    _cached_git_repository: Path, git_exe: str, tmp_path_factory, request
) -> Path:
    """Create a git repository that contains a submodule."""
    directory = tmp_path_factory.mktemp("cached_submodule_repository")
    shutil.copytree(_cached_git_repository, directory, dirs_exist_ok=True)
    header = cleandoc(
        """
            SPDX-FileCopyrightText: 2019 Jane Doe

            SPDX-License-Identifier: CC0-1.0
            """
    )

    submodule = tmp_path_factory.mktemp("submodule")
    (submodule / "foo.py").write_text(header, encoding="utf-8")

    os.chdir(submodule)

    subprocess.run([git_exe, "init", str(submodule)], check=True)
    Path(".git/config").write_text(
        cleandoc(
            """
            [user]
              name = Example
              email = example@example.com
            [commit]
              gpgSign = false
            """
        ),
        encoding="utf-8",
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

    os.chdir(directory)

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
            directory / ".gitmodules", mode="a", encoding="utf-8"
        ) as gitmodules_file:
            gitmodules_file.write(
                cleandoc(
                    f"""
                    [submodule "submodule"]
                      path = submodule
                      url = {submodule.resolve().as_posix()}
                    """
                )
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
    (directory / ".gitmodules.license").write_text(header)

    return directory


@pytest.fixture()
def submodule_repository(_cached_submodule_repository, tmp_path) -> Path:
    """Create a git repository that contains a submodule."""
    shutil.copytree(_cached_submodule_repository, tmp_path, dirs_exist_ok=True)
    os.chdir(tmp_path)
    return tmp_path


@pytest.fixture()
def subproject_repository(fake_repository: Path) -> Path:
    """Add a Meson subproject to the fake repo."""
    (fake_repository / "meson.build").write_text(
        cleandoc(
            """
            SPDX-FileCopyrightText: 2022 Jane Doe
            SPDX-License-Identifier: CC0-1.0
            """
        )
    )
    subprojects_dir = fake_repository / "subprojects"
    subprojects_dir.mkdir()
    libfoo_dir = subprojects_dir / "libfoo"
    libfoo_dir.mkdir()
    # ./subprojects/foo.wrap has license and linter succeeds
    (subprojects_dir / "foo.wrap").write_text(
        cleandoc(
            """
            SPDX-FileCopyrightText: 2022 Jane Doe
            SPDX-License-Identifier: CC0-1.0
            """
        )
    )
    # ./subprojects/libfoo/foo.c misses license but is ignored
    (libfoo_dir / "foo.c").write_text("foo")
    return fake_repository


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
        """
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
