"""The repository-level documents copied into the shipped manual."""

from __future__ import annotations

import sys
from pathlib import Path

from outrage import shipped

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "tools"))

import copy_project_documents  # noqa: E402


def test_the_shipped_project_documents_are_current():
    destination = shipped.tree() / "project"

    for source_name, destination_name in copy_project_documents.PROJECT_DOCUMENTS.items():
        assert (destination / destination_name).read_bytes() == (
            REPOSITORY / source_name
        ).read_bytes()


def test_copying_project_documents_creates_the_destination(tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    for name in copy_project_documents.PROJECT_DOCUMENTS:
        (repository / name).write_text(f"contents of {name}\n")

    destination = tmp_path / "manual" / "project"
    written = copy_project_documents.copy_documents(repository, destination)

    assert written == [
        destination / name for name in copy_project_documents.PROJECT_DOCUMENTS.values()
    ]
    assert [path.read_text() for path in written] == [
        f"contents of {name}\n" for name in copy_project_documents.PROJECT_DOCUMENTS
    ]
