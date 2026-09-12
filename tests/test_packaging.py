"""Checks on what a release actually ships.

The suite already guards that the packaged files are *in the checkout* -
``test_skill.py`` and ``test_agents.py`` do that. Nothing guarded that they
reach the artefacts, and 0.1.0 went to PyPI without ``src/outrage/skills/``:
the build walked a dogfooding symlink, claimed the inode under ``.claude`` and
skipped the real directory. Every test passed, because a test that reads the
checkout cannot see what the build dropped. ``context/48/findings`` in the outrage
store has the whole of it.

So these tests build the artefacts and read them. The build follows the path a
release takes - sdist first, then the wheel *from that sdist* - because that is
the sequence the bug lived in: ``pip wheel`` produced a correct wheel from the
same commit, since the wheel target roots its own walk at ``src/outrage`` and
never crosses ``.claude``.

It costs about half a second, which is why it runs by default rather than
behind a flag. It needs ``hatchling`` and ``build``, both in the ``dev`` extra.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path

import pytest

import outrage

REPO = Path(__file__).resolve().parents[1]
PACKAGE = REPO / "src" / "outrage"

# Read rather than imported from the root ``conftest.py``: two files of that
# name, and importing one of them by name is a coin toss.
TEST_INSTALLED = bool(os.environ.get("OUTRAGE_TEST_INSTALLED"))


def test_documents_extra_installs_the_bounded_common_format_readers():
    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert project["optional-dependencies"]["documents"] == [
        "markitdown[docx,pdf,pptx,xlsx]>=0.1.7,<0.2"
    ]


def test_the_all_extra_names_every_extra_but_the_ones_for_working_on_outrage():
    """`all` is what the README says to install, so an extra it misses is one
    nobody following the README gets, with nothing to say so."""
    extras = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "optional-dependencies"
    ]
    wanted = sorted(set(extras) - {"all", "dev", "docs"})

    (named,) = extras["all"]
    assert named.startswith("outrage[") and named.endswith("]")
    assert sorted(named.removeprefix("outrage[").removesuffix("]").split(",")) == wanted


def _data_files() -> list[str]:
    """Every non-Python file under ``src/outrage``, package-relative.

    These are what a build can silently drop. Python modules cannot go missing
    quietly - the suite stops importing - so they are not the risk here.
    """
    found = []
    for path in PACKAGE.rglob("*"):
        if not path.is_file() or path.suffix == ".py":
            continue
        rel = path.relative_to(PACKAGE)
        if "__pycache__" in rel.parts or any(part.startswith(".") for part in rel.parts):
            continue
        found.append(rel.as_posix())
    return sorted(found)


@pytest.fixture(scope="session")
def artefacts(tmp_path_factory) -> tuple[Path, Path]:
    """Build the sdist and the wheel from it, returning both paths."""
    for module in ("build", "hatchling"):
        pytest.importorskip(
            module,
            reason=f"{module} is needed to build the artefacts; install the dev extra",
        )

    out = tmp_path_factory.mktemp("dist")
    # --no-isolation so this needs no network: the build dependencies are the
    # dev extra's, already installed, rather than a fresh venv's download.
    result = subprocess.run(
        [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(out), str(REPO)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, f"build failed:\n{result.stdout}\n{result.stderr}"

    sdists = list(out.glob("*.tar.gz"))
    wheels = list(out.glob("*.whl"))
    assert len(sdists) == 1 and len(wheels) == 1, f"expected one of each, got {list(out.iterdir())}"
    return sdists[0], wheels[0]


@pytest.fixture(scope="session")
def sdist_names(artefacts) -> set[str]:
    """Sdist members, with the ``outrage-<version>/`` prefix stripped."""
    sdist, _ = artefacts
    with tarfile.open(sdist) as archive:
        return {name.partition("/")[2] for name in archive.getnames()}


@pytest.fixture(scope="session")
def wheel_names(artefacts) -> set[str]:
    _, wheel = artefacts
    with zipfile.ZipFile(wheel) as archive:
        return set(archive.namelist())


def test_the_checkout_is_what_is_under_test():
    # Says out loud which copy the whole run is about. Without this the answer
    # is an environment detail nobody states, and a green run against an
    # installed release reads exactly like a green run against the checkout.
    where = Path(outrage.__file__).resolve().parent
    if TEST_INSTALLED:
        assert where != PACKAGE.resolve(), (
            "OUTRAGE_TEST_INSTALLED is set, but the checkout is still what imports"
        )
    else:
        assert where == PACKAGE.resolve(), (
            f"the suite is testing {where}, not this checkout; an installed copy is shadowing src/"
        )


def test_there_are_data_files_to_lose():
    # The checks below iterate this list, so an empty one would pass them all
    # while asserting nothing. The skill is named because it is the file that
    # actually went missing.
    files = _data_files()
    assert "skills/outrage/SKILL.md" in files
    assert "codex/skills/outrage/SKILL.md" in files
    # The documentation store, which is shipped for the same reason and is lost
    # the same way. A tree rather than one file, so the *whole* of it has to
    # travel: a wheel carrying the readme and nothing else would mount, read as
    # a manual with four documents missing, and say nothing about it.
    assert "documents/readme.md" in files
    assert len(files) >= 5, files


def test_the_documentation_tree_travels_whole(sdist_names, wheel_names):
    """Every file of it, not merely some. See the comment above."""
    tree = [rel for rel in _data_files() if rel.startswith("documents/")]

    assert len(tree) >= 5, tree
    assert not [rel for rel in tree if f"src/outrage/{rel}" not in sdist_names]
    assert not [rel for rel in tree if f"outrage/{rel}" not in wheel_names]


def test_the_sdist_carries_every_data_file(sdist_names):
    missing = [rel for rel in _data_files() if f"src/outrage/{rel}" not in sdist_names]
    assert not missing, f"the sdist dropped {missing}"


def test_the_wheel_carries_every_data_file(wheel_names):
    missing = [rel for rel in _data_files() if f"outrage/{rel}" not in wheel_names]
    assert not missing, f"the wheel dropped {missing}"


def test_the_sdist_leaves_out_the_dogfood_config_and_sibling_distribution(sdist_names):
    # `.claude` is this project's own configuration, of no use to anyone
    # installing outrage - and excluding it is half of what stops the symlink
    # from eating the skill. The other half is `skip-excluded-dirs`, without
    # which the walk still descends and still claims the inode.
    #
    # `.mcp.json` is the same file's neighbour: this repository registering the
    # server for itself, naming a conda environment and a OneDrive folder that
    # exist on one machine. It shipped in 0.3.0 and in the first 0.4.0 build.
    # `import/` is a separate distribution with its own dependencies and
    # release cycle; installing outrage must not carry a second source tree.
    intruders = [
        name
        for name in sdist_names
        if name.startswith((".claude", "import/")) or name == ".mcp.json"
    ]
    assert not intruders, intruders


def test_the_licence_travels(sdist_names, wheel_names):
    assert "LICENSE" in sdist_names
    licences = [name for name in wheel_names if name.endswith(".dist-info/licenses/LICENSE")]
    assert licences, "the wheel carries no LICENSE"


def _metadata(raw: bytes) -> dict[str, str]:
    return dict(BytesParser().parsebytes(raw).items())


def test_the_artefacts_carry_the_running_version(artefacts, sdist_names, wheel_names):
    # The end of the drift question: whatever `outrage.__version__` says is
    # what the metadata and the filenames say, or the build is describing
    # something other than the code in it.
    sdist, wheel = artefacts
    version = outrage.__version__

    assert sdist.name == f"outrage-{version}.tar.gz"
    assert wheel.name.startswith(f"outrage-{version}-")

    with tarfile.open(sdist) as archive:
        member = next(name for name in archive.getnames() if name.endswith("/PKG-INFO"))
        pkg_info = _metadata(archive.extractfile(member).read())
    assert pkg_info["Version"] == version
    assert pkg_info["Metadata-Version"] == "2.4"
    assert pkg_info["License-Expression"] == "MIT"

    with zipfile.ZipFile(wheel) as archive:
        member = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
        metadata = _metadata(archive.read(member))
    assert metadata["Version"] == version
    assert metadata["Metadata-Version"] == "2.4"
    assert metadata["License-Expression"] == "MIT"


def test_the_version_has_one_source():
    # Cheap, and unlike the test above it still runs when the build tools are
    # missing. `pyproject.toml` carried its own copy of the version until
    # 0.1.1, and nothing compared the two.
    config = tomllib.loads((REPO / "pyproject.toml").read_text())
    assert "version" not in config["project"], "pyproject.toml is carrying a second version"
    assert "version" in config["project"]["dynamic"]
    assert config["tool"]["hatch"]["version"]["path"] == "src/outrage/__init__.py"
