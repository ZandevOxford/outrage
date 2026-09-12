from __future__ import annotations

import bz2
import hashlib
import io
import xml.etree.ElementTree as ET
from argparse import Namespace
from pathlib import Path

import pytest
from outrage.store import BoundedSubtree
from outrage.store_duckdb import DuckdbStore

from wikiimport import cli
from wikiimport import source as source_module
from wikiimport.convert import Conversion, convert_part
from wikiimport.fetch import FetchError, fetch_part
from wikiimport.markdown import to_markdown
from wikiimport.pages import read_pages
from wikiimport.source import _PART, _SUM, Part, SourceError, _chosen_date, _links
from wikiimport.titles import TitleError, link_to_key, title_to_key


def test_titles_are_mapped_injectively_without_flattening_subpages():
    assert title_to_key("Alan Turing") == "Alan Turing"
    assert title_to_key("AC/DC") == "AC/DC"
    assert title_to_key("!!!") == "#!!!"
    assert title_to_key("?") == "#?"
    assert title_to_key("007") == "#007"
    assert title_to_key("10") == "10"
    assert link_to_key("007#Cast") == "#007#Cast"
    with pytest.raises(TitleError):
        title_to_key("not#a-title")


def test_wikitext_conversion_keeps_prose_and_drops_expansion_only_markup():
    source = """'''Lead''' and ''stress'' with [[Alan Turing|a link]] &amp; [https://e.test site].

{{Infobox|lost=yes}}
== History ==
* first
# second
<ref>a citation</ref>[[File:Example.jpg|thumb]]
{| class="wikitable"
| hidden
|}
Tail.
"""
    assert to_markdown(source) == (
        "**Lead** and *stress* with [a link](Alan Turing) & [site](https://e.test).\n\n"
        "## History\n\n- first\n1. second\n\nTail.\n"
    )


def _dump(path: Path, pages: list[dict[str, object]]) -> None:
    root = ET.Element("mediawiki", xmlns="http://www.mediawiki.org/xml/export-0.11/")
    for values in pages:
        page = ET.SubElement(root, "page")
        ET.SubElement(page, "title").text = str(values["title"])
        ET.SubElement(page, "ns").text = str(values.get("namespace", 0))
        ET.SubElement(page, "id").text = str(values.get("id", 1))
        if values.get("redirect") is not None:
            ET.SubElement(page, "redirect", title=str(values["redirect"]))
        revision = ET.SubElement(page, "revision")
        ET.SubElement(revision, "timestamp").text = str(
            values.get("timestamp", "2026-09-01T12:00:00Z")
        )
        ET.SubElement(revision, "model").text = "wikitext"
        ET.SubElement(revision, "text").text = str(values.get("text", ""))
    path.write_bytes(bz2.compress(ET.tostring(root, encoding="utf-8", xml_declaration=True)))


def _part(path: Path, first: int, last: int) -> Part:
    data = path.read_bytes()
    return Part(
        name=path.name,
        url=path.as_uri(),
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        first_page=first,
        last_page=last,
    )


def test_pages_stream_only_selected_namespaces(tmp_path):
    source = tmp_path / "sample.xml.bz2"
    _dump(
        source,
        [
            {"title": "Article", "text": "body"},
            {"title": "Talk:Article", "namespace": 1, "text": "discussion"},
        ],
    )
    assert [page.title for page in read_pages(source, frozenset({0}))] == ["Article"]
    assert [page.title for page in read_pages(source, frozenset({0, 1}))] == [
        "Article",
        "Talk:Article",
    ]


def test_independent_pieces_form_one_store_and_cross_part_aliases_accumulate(tmp_path):
    first = tmp_path / "wiki-2026-09-01-p1p2.xml.bz2"
    second = tmp_path / "wiki-2026-09-01-p3p4.xml.bz2"
    _dump(
        first,
        [
            {"title": "Zed", "text": "A [[Later]] page."},
            {"title": "Alias", "redirect": "Later", "text": "#REDIRECT [[Later]]"},
        ],
    )
    _dump(
        second,
        [
            {"title": "Later", "text": "'''Arrived''' later."},
            {"title": "Second alias", "redirect": "Later", "text": "#REDIRECT [[Later]]"},
        ],
    )
    target = tmp_path / "store"
    receipts = tmp_path / "receipts"
    one, changed = convert_part(_part(first, 1, 2), first, target, receipts)
    assert changed and one.rows == 3
    two, changed = convert_part(_part(second, 3, 4), second, target, receipts)
    assert changed and two.rows == 3

    with DuckdbStore(tmp_path, filename="store") as store:
        assert store.retrieve_document("Zed").content == "A [Later](Later) page.\n"
        assert store.retrieve_document("Later").content == "**Arrived** later.\n"
        aliases = store.get_documents(BoundedSubtree(key="Later/!aliases"))
        assert sorted(item.content for item in aliases.items) == ["Alias", "Second alias"]

    reused, changed = convert_part(_part(first, 1, 2), first, target, receipts)
    assert not changed and reused == one


def test_apache_indexes_and_control_lines_are_recognised():
    page = b'<a href="2026-09-01/">2026-09-01/</a> 01-Sep-2026 00:00 -\n'
    assert _links(page) == [("2026-09-01/", None)]
    assert _chosen_date(_links(page), "2026-09") == "2026-09-01"
    assert _PART.fullmatch("enwiki-2026-09-01-p10p20.xml.bz2")
    assert _SUM.fullmatch("a" * 64 + "  enwiki-2026-09-01-p10p20.xml.bz2")
    with pytest.raises(SourceError):
        _chosen_date(_links(page), "2026-08")


def test_resolve_requires_success_and_orders_parts_by_numeric_page_id(monkeypatch):
    root = "https://example.test/"
    wiki = root + "enwiki/"
    dump = wiki + "2026-09-01/xml/bzip2/"
    late = "enwiki-2026-09-01-p8008467p13070023.xml.bz2"
    early = "enwiki-2026-09-01-p10p1118752.xml.bz2"
    pages = {
        wiki: b'<a href="2026-09-01/">2026-09-01/</a> -\n',
        dump: (
            f'<a href="_SUCCESS">_SUCCESS</a> -\n'
            f'<a href="SHA256SUMS">SHA256SUMS</a> 100\n'
            f'<a href="{late}">{late}</a> 01-Sep-2026 00:00 20\n'
            f'<a href="{early}">{early}</a> 01-Sep-2026 00:00 10\n'
        ).encode(),
        dump + "SHA256SUMS": f"{'a' * 64}  {late}\n{'b' * 64}  {early}\n".encode(),
    }
    monkeypatch.setattr(source_module, "_read", pages.__getitem__)
    resolved = source_module.resolve(source_url=root, wiki="enwiki", files=1)
    assert [part.name for part in resolved.parts] == [early]

    pages[dump] = pages[dump].replace(b'<a href="_SUCCESS">_SUCCESS</a> -\n', b"")
    with pytest.raises(SourceError, match="_SUCCESS"):
        source_module.resolve(source_url=root, wiki="enwiki")


def test_the_default_pipeline_converts_each_piece_before_fetching_the_next(
    tmp_path, monkeypatch, capsys
):
    parts = tuple(
        Part(f"wiki-2026-09-01-p{n}p{n}.xml.bz2", f"https://e/{n}", 1, "0" * 64, n, n)
        for n in (1, 2)
    )
    dump = source_module.Dump("wiki", "2026-09-01", "https://e/", parts)
    events = []

    monkeypatch.setattr(cli, "resolve", lambda **kwargs: dump)

    def fetched(part, directory):
        events.append(("fetch", part.first_page))
        return tmp_path / part.name, True

    def converted(part, source, target, receipts, **kwargs):
        events.append(("convert", part.first_page))
        receipt = Conversion(
            part.name, part.sha256, "0.1.0", (0,), True, 1, f"{part.first_page}.parquet"
        )
        return receipt, True

    monkeypatch.setattr(cli, "fetch_part", fetched)
    monkeypatch.setattr(cli, "convert_part", converted)
    cli.run(
        Namespace(
            download_dir=tmp_path,
            source_url="https://e/",
            wiki="wiki",
            month=None,
            files=None,
            target=None,
            namespaces=None,
            redirects=True,
            jobs=1,
            stage="all",
            dry_run=False,
            overwrite=False,
        )
    )
    assert events == [("fetch", 1), ("convert", 1), ("fetch", 2), ("convert", 2)]
    assert "wrote 2.parquet" in capsys.readouterr().out


def test_a_partial_download_resumes_and_only_the_verified_name_appears(tmp_path, monkeypatch):
    content = b"a complete compressed part"
    remote = Part(
        name="wiki-2026-09-01-p1p2.xml.bz2",
        url="https://example.test/part",
        size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        first_page=1,
        last_page=2,
    )
    partial = tmp_path / f".{remote.name}.part"
    partial.write_bytes(content[:7])
    requests = []

    class Response(io.BytesIO):
        status = 206
        headers = {"Content-Range": f"bytes 7-{len(content) - 1}/{len(content)}"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

        def getcode(self):
            return self.status

    def open_request(request):
        requests.append(request)
        return Response(content[7:])

    monkeypatch.setattr("urllib.request.urlopen", open_request)
    path, changed = fetch_part(remote, tmp_path)
    assert changed and path.read_bytes() == content
    assert requests[0].get_header("Range") == "bytes=7-"
    assert not partial.exists()

    _, changed = fetch_part(remote, tmp_path)
    assert not changed
    assert len(requests) == 1


def test_a_checksum_mismatch_never_promotes_a_partial_download(tmp_path, monkeypatch):
    content = b"wrong"
    remote = Part(
        name="wiki-2026-09-01-p1p2.xml.bz2",
        url="https://example.test/part",
        size=len(content),
        sha256="0" * 64,
        first_page=1,
        last_page=2,
    )

    class Response(io.BytesIO):
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

        def getcode(self):
            return self.status

    monkeypatch.setattr("urllib.request.urlopen", lambda request: Response(content))
    with pytest.raises(FetchError, match="SHA-256 mismatch"):
        fetch_part(remote, tmp_path)
    assert not (tmp_path / remote.name).exists()


def test_a_complete_verified_partial_is_promoted_without_downloading(tmp_path, monkeypatch):
    content = b"complete before the interrupted rename"
    remote = Part(
        name="wiki-2026-09-01-p1p2.xml.bz2",
        url="https://example.test/part",
        size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        first_page=1,
        last_page=2,
    )
    (tmp_path / f".{remote.name}.part").write_bytes(content)
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request: pytest.fail("a complete partial file must not be downloaded again"),
    )
    path, changed = fetch_part(remote, tmp_path)
    assert changed and path.read_bytes() == content
