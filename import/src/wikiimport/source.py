"""Resolve a completed Wikimedia dump and select its parts."""

from __future__ import annotations

import re
import urllib.request
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urljoin

DEFAULT_SOURCE = "https://dumps.wikimedia.org/other/mediawiki_content_current/"

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MONTH = re.compile(r"^\d{4}-\d{2}$")
_LINK = re.compile(r'<a\s+href="([^"]+)"[^>]*>.*?</a>([^\r\n]*)', re.IGNORECASE)
_PART = re.compile(
    r"^(?P<wiki>[A-Za-z0-9_]+)-(?P<date>\d{4}-\d{2}-\d{2})-p"
    r"(?P<first>\d+)p(?P<last>\d+)\.xml\.bz2$"
)
_SIZE = re.compile(r"(\d+)\s*$")
_SUM = re.compile(r"^(?P<digest>[0-9a-fA-F]{64})\s+[* ]?(?P<name>\S+)\s*$")


class SourceError(RuntimeError):
    """The remote dump does not have the complete shape the importer needs."""


@dataclass(frozen=True)
class Part:
    """One selected XML part and the facts needed to fetch it safely."""

    name: str
    url: str
    size: int
    sha256: str
    first_page: int
    last_page: int


@dataclass(frozen=True)
class Dump:
    """One completed monthly dump."""

    wiki: str
    date: str
    url: str
    parts: tuple[Part, ...]


def _read(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "outrage-wikiimport/0.1"})
    with urllib.request.urlopen(request) as response:  # noqa: S310 - caller chooses source URL
        return response.read()


def _links(page: bytes) -> list[tuple[str, int | None]]:
    text = page.decode("utf-8", errors="replace")
    found: list[tuple[str, int | None]] = []
    for href, tail in _LINK.findall(text):
        size = _SIZE.search(tail)
        found.append((href, int(size.group(1)) if size else None))
    return found


def _chosen_date(links: list[tuple[str, int | None]], month: str | None) -> str:
    dates = sorted(href.rstrip("/") for href, _ in links if _DATE.fullmatch(href.rstrip("/")))
    if not dates:
        raise SourceError("the wiki index contains no dated dumps")
    if month is None:
        return dates[-1]
    if _DATE.fullmatch(month):
        if month not in dates:
            raise SourceError(f"dump date {month} does not exist")
        return month
    if not _MONTH.fullmatch(month):
        raise SourceError("--month must be YYYY-MM or YYYY-MM-DD")
    matches = [date for date in dates if date.startswith(month + "-")]
    if not matches:
        raise SourceError(f"dump month {month} does not exist")
    return matches[-1]


def _checksums(data: bytes) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in data.decode("ascii").splitlines():
        match = _SUM.fullmatch(line)
        if match:
            out[PurePosixPath(match.group("name")).name] = match.group("digest").lower()
    return out


def resolve(
    *,
    source_url: str = DEFAULT_SOURCE,
    wiki: str = "enwiki",
    month: str | None = None,
    files: int | None = None,
) -> Dump:
    """Resolve and validate one completed dump, ordered by numeric page id."""
    if not re.fullmatch(r"[A-Za-z0-9_]+", wiki):
        raise SourceError("--wiki may contain only letters, digits and underscores")
    if files is not None and files < 1:
        raise SourceError("--files must be at least 1")

    root = source_url.rstrip("/") + "/"
    wiki_url = urljoin(root, wiki + "/")
    date = _chosen_date(_links(_read(wiki_url)), month)
    dump_url = urljoin(wiki_url, f"{date}/xml/bzip2/")
    links = _links(_read(dump_url))
    names = {href.rstrip("/") for href, _ in links}
    if "_SUCCESS" not in names:
        raise SourceError(f"dump {wiki}/{date} is incomplete: _SUCCESS is missing")
    if "SHA256SUMS" not in names:
        raise SourceError(f"dump {wiki}/{date} has no SHA256SUMS")
    sums = _checksums(_read(urljoin(dump_url, "SHA256SUMS")))

    parts: list[Part] = []
    for href, size in links:
        name = PurePosixPath(href).name
        match = _PART.fullmatch(name)
        if match is None or match.group("wiki") != wiki or match.group("date") != date:
            continue
        if size is None:
            raise SourceError(f"the index gives no size for {name}")
        if name not in sums:
            raise SourceError(f"SHA256SUMS does not name {name}")
        parts.append(
            Part(
                name=name,
                url=urljoin(dump_url, href),
                size=size,
                sha256=sums[name],
                first_page=int(match.group("first")),
                last_page=int(match.group("last")),
            )
        )
    parts.sort(key=lambda part: part.first_page)
    if not parts:
        raise SourceError(f"dump {wiki}/{date} contains no XML parts")
    if files is not None:
        parts = parts[:files]
    return Dump(wiki=wiki, date=date, url=dump_url, parts=tuple(parts))


__all__ = ["DEFAULT_SOURCE", "Dump", "Part", "SourceError", "resolve"]
