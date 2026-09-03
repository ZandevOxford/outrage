"""The deterministic local-file boundary around optional MarkItDown conversion."""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

from outrage import ingest
from outrage.mounts import MountedStore, ReadOnlyMountError
from outrage.store_sqlite import SqliteStore


class _MarkItDownException(Exception):
    pass


class _MissingDependencyException(_MarkItDownException):
    pass


class _UnsupportedFormatException(_MarkItDownException):
    pass


class _FileConversionException(_MarkItDownException):
    def __init__(self, message="conversion failed", attempts=None):
        super().__init__(message)
        self.attempts = attempts


def _fake_markitdown(monkeypatch, *, markdown="# Converted", title="Detected", failure=None):
    calls = []

    class MarkItDown:
        def __init__(self, **kwargs):
            calls.append(("init", kwargs))

        def convert_local(self, path):
            calls.append(("convert_local", path))
            if failure is not None:
                raise failure
            return SimpleNamespace(markdown=markdown, title=title)

    module = ModuleType("markitdown")
    module.MarkItDown = MarkItDown
    module.MarkItDownException = _MarkItDownException
    module.MissingDependencyException = _MissingDependencyException
    module.UnsupportedFormatException = _UnsupportedFormatException
    module.FileConversionException = _FileConversionException
    monkeypatch.setitem(sys.modules, "markitdown", module)
    return calls


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "Quarterly report.docx"
    path.write_bytes(b"not interpreted by the fake")
    return path


@pytest.fixture
def store(tmp_path):
    with SqliteStore(tmp_path / "store") as opened:
        yield opened


def test_importing_ingest_does_not_import_markitdown():
    assert "markitdown" not in sys.modules


def test_conversion_is_local_plugins_are_off_and_markdown_is_stored(
    store, source, monkeypatch
):
    calls = _fake_markitdown(monkeypatch, markdown="# Body\n", title="From file")

    result = ingest.ingest_document(store, source, "/reference//report/")

    assert calls == [("init", {"enable_plugins": False}), ("convert_local", source.resolve())]
    assert result == ingest.IngestResult(
        source=source.resolve(),
        key="reference/report",
        title="From file",
        characters=7,
        format="markdown",
        title_key="reference/report/!title",
        dry_run=False,
    )
    written = store.retrieve_document("reference/report")
    assert (written.content, written.format) == ("# Body\n", "markdown")
    assert store.retrieve_document("reference/report/!title").content == "From file"
    assert not store.exists("reference/report/!source")


@pytest.mark.parametrize(
    ("explicit", "detected", "expected"),
    [
        ("Chosen", "Detected", "Chosen"),
        (None, "Detected", "Detected"),
        (None, None, "Quarterly report"),
    ],
)
def test_title_precedence(store, source, monkeypatch, explicit, detected, expected):
    _fake_markitdown(monkeypatch, title=detected)

    result = ingest.ingest_document(store, source, "document", title=explicit)

    assert result.title == expected
    assert store.retrieve_document("document/!title").content == expected


def test_dry_run_converts_and_writes_nothing(store, source, monkeypatch):
    calls = _fake_markitdown(monkeypatch, markdown="preview", title=None)

    result = ingest.ingest_document(store, source, "document", dry_run=True)

    assert calls[-1] == ("convert_local", source.resolve())
    assert result.characters == 7
    assert result.title == "Quarterly report"
    assert result.title_key is None
    assert result.dry_run is True
    assert not store.exists("document")


def test_existing_destination_is_preserved_unless_overwrite(store, source, monkeypatch):
    _fake_markitdown(monkeypatch, markdown="new")
    store.store_document("document", "mine")

    with pytest.raises(ingest.IngestError) as raised:
        ingest.ingest_document(store, source, "document")
    assert raised.value.code == "ingest-target-exists"
    assert store.retrieve_document("document").content == "mine"

    ingest.ingest_document(store, source, "document", overwrite=True)
    assert store.retrieve_document("document").content == "new"


def test_existing_title_alone_also_occupies_the_destination(store, source, monkeypatch):
    _fake_markitdown(monkeypatch, markdown="new")
    store.store_document("document/!title", "mine")

    with pytest.raises(ingest.IngestError) as raised:
        ingest.ingest_document(store, source, "document")

    assert raised.value.code == "ingest-target-exists"
    assert store.retrieve_document("document/!title").content == "mine"


def test_destination_routes_through_a_writable_mount(store, source, tmp_path, monkeypatch):
    _fake_markitdown(monkeypatch)
    with SqliteStore(tmp_path / "mounted") as mounted:
        table = MountedStore({"": store, "ref": mounted})

        result = ingest.ingest_document(table, source, "ref/document")

        assert result.key == "ref/document"
        assert result.title_key == "ref/document/!title"
        assert mounted.retrieve_document("document").format == "markdown"
        assert not store.exists("ref/document")


def test_read_only_mount_refuses_the_write(store, source, tmp_path, monkeypatch):
    _fake_markitdown(monkeypatch)
    with SqliteStore(tmp_path / "mounted") as mounted:
        table = MountedStore({"": store, "ref": mounted}, read_only={"ref"})

        with pytest.raises(ReadOnlyMountError):
            ingest.ingest_document(table, source, "ref/document")

        assert not mounted.exists("document")


@pytest.mark.parametrize("source_name", ["https://example.com/a.pdf", "file:///tmp/a.pdf"])
def test_urls_are_refused_before_markitdown_is_imported(store, source_name):
    with pytest.raises(ingest.IngestError) as raised:
        ingest.ingest_document(store, source_name, "document")
    assert raised.value.code == "ingest-source-url"


def test_a_directory_and_a_missing_path_are_bad_sources(store, tmp_path):
    for source in (tmp_path, tmp_path / "missing.pdf"):
        with pytest.raises(ingest.IngestError) as raised:
            ingest.ingest_document(store, source, "document")
        assert raised.value.code == "ingest-source-not-file"


def test_absent_optional_extra_is_an_outrage_error(store, source, monkeypatch):
    monkeypatch.setitem(sys.modules, "markitdown", None)

    with pytest.raises(ingest.IngestError) as raised:
        ingest.ingest_document(store, source, "document")

    assert raised.value.code == "ingest-documents-extra-missing"


def test_unsupported_format_is_distinct_from_conversion_failure(store, source, monkeypatch):
    _fake_markitdown(monkeypatch, failure=_UnsupportedFormatException("no converter"))

    with pytest.raises(ingest.IngestError) as raised:
        ingest.ingest_document(store, source, "document")

    assert raised.value.code == "ingest-format-unsupported"


def test_wrapped_missing_converter_dependency_is_recognised(store, source, monkeypatch):
    missing = _MissingDependencyException("install the pdf\nreader")
    attempt = SimpleNamespace(exc_info=(_MissingDependencyException, missing, None))
    _fake_markitdown(
        monkeypatch, failure=_FileConversionException("one attempt failed", [attempt])
    )

    with pytest.raises(ingest.IngestError) as raised:
        ingest.ingest_document(store, source, "document")

    assert raised.value.code == "ingest-converter-dependency-missing"
    assert "\n" not in raised.value.details["reason"]


def test_other_conversion_failures_are_reported(store, source, monkeypatch):
    _fake_markitdown(monkeypatch, failure=_FileConversionException("broken input"))

    with pytest.raises(ingest.IngestError) as raised:
        ingest.ingest_document(store, source, "document")

    assert raised.value.code == "ingest-conversion-failed"


def test_real_plain_text_conversion_when_the_extra_is_installed(store, tmp_path):
    pytest.importorskip("markitdown")
    source = tmp_path / "note.txt"
    source.write_text("A real conversion.\n", encoding="utf-8")

    result = ingest.ingest_document(store, source, "real")

    assert "A real conversion." in store.retrieve_document("real").content
    assert result.format == "markdown"
