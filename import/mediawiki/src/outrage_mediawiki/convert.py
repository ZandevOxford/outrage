"""Convert one verified dump piece into one atomic Parquet store part."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path

from outrage.store_parquet import ParquetStore

from . import __version__
from .markdown import to_markdown
from .pages import read_pages
from .source import Part
from .titles import title_to_key


class ConvertError(RuntimeError):
    """An existing output cannot safely be reused or replaced implicitly."""


@dataclass(frozen=True)
class Conversion:
    """The durable receipt for one converted dump piece."""

    source: str
    sha256: str
    importer_version: str
    namespaces: tuple[int, ...]
    redirects: bool
    rows: int
    target: str


def output_name(part: Part) -> str:
    """The stable store-part name corresponding to one Wikimedia piece."""
    return f"p{part.first_page}p{part.last_page}.parquet"


def _alias_key(target: str, alias: str) -> str:
    digest = hashlib.sha256(alias.encode()).hexdigest()
    return f"{title_to_key(target.partition('#')[0])}/!aliases/{digest}"


def _rows(
    path: Path, namespaces: frozenset[int], redirects: bool
) -> Iterator[tuple[str, str, str | None, str | None]]:
    for page in read_pages(path, namespaces):
        if page.redirect is not None:
            if redirects:
                yield _alias_key(page.redirect, page.title), page.title, "markdown", page.timestamp
            continue
        key = title_to_key(page.title)
        yield key, to_markdown(page.text), "markdown", page.timestamp
        yield f"{key}/!title", page.title, "markdown", page.timestamp


def _receipt(path: Path) -> Conversion | None:
    try:
        values = json.loads(path.read_text())
        values["namespaces"] = tuple(values["namespaces"])
        return Conversion(**values)
    except (FileNotFoundError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return None


def convert_part(
    part: Part,
    source: str | os.PathLike[str],
    target_directory: str | os.PathLike[str],
    receipt_directory: str | os.PathLike[str],
    *,
    namespaces: frozenset[int] = frozenset({0}),
    redirects: bool = True,
    overwrite: bool = False,
) -> tuple[Conversion, bool]:
    """Convert one piece, reusing only an output with a matching receipt."""
    source_path = Path(source)
    target_dir = Path(target_directory).expanduser()
    receipts = Path(receipt_directory).expanduser()
    target = target_dir / output_name(part)
    receipt_path = receipts / f"{output_name(part)}.json"
    expected = {
        "source": part.name,
        "sha256": part.sha256,
        "importer_version": __version__,
        "namespaces": tuple(sorted(namespaces)),
        "redirects": redirects,
        "target": target.name,
    }
    prior = _receipt(receipt_path)
    if target.exists() and prior is not None:
        facts = asdict(prior)
        if all(facts[name] == value for name, value in expected.items()):
            return prior, False
    if target.exists() and not overwrite:
        raise ConvertError(f"{target} exists without a matching conversion receipt")

    target_dir.mkdir(parents=True, exist_ok=True)
    rows = ParquetStore.build_part(
        target, _rows(source_path, namespaces, redirects), overwrite=True
    )
    completed = Conversion(rows=rows, **expected)
    receipts.mkdir(parents=True, exist_ok=True)
    temporary = receipt_path.with_name(f".{receipt_path.name}.tmp")
    temporary.write_text(json.dumps(asdict(completed), indent=2, sort_keys=True) + "\n")
    os.replace(temporary, receipt_path)
    return completed, True


__all__ = ["Conversion", "ConvertError", "convert_part", "output_name"]
