"""Resumable, checksum-verified fetching of Wikimedia parts."""

from __future__ import annotations

import hashlib
import os
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO

from .source import Part

CHUNK_SIZE = 1024 * 1024


class FetchError(RuntimeError):
    """A downloaded part was incomplete or did not match its published hash."""


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file without reading it whole."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _seed(path: Path, digest: object) -> int:
    size = 0
    if path.exists():
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
                digest.update(chunk)
                size += len(chunk)
    return size


def fetch_part(
    part: Part,
    directory: str | os.PathLike[str],
    *,
    progress: Callable[[int], None] | None = None,
) -> tuple[Path, bool]:
    """Fetch one part, resuming a partial file and verifying before rename.

    Returns ``(path, downloaded)``. A verified final file is reused. Bytes are
    appended to ``<name>.part`` and the final name appears atomically only
    after its length and SHA-256 digest match Wikimedia's control files.
    """
    destination = Path(directory).expanduser()
    destination.mkdir(parents=True, exist_ok=True)
    final = destination / part.name
    partial = destination / f".{part.name}.part"

    if final.exists() and final.stat().st_size == part.size:
        if sha256_file(final) == part.sha256:
            return final, False

    digest = hashlib.sha256()
    offset = _seed(partial, digest)
    if offset == part.size and digest.hexdigest() == part.sha256:
        os.replace(partial, final)
        return final, True
    if offset >= part.size:
        partial.unlink()
        digest = hashlib.sha256()
        offset = 0

    headers = {"User-Agent": "outrage-wikiimport/0.1"}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    request = urllib.request.Request(part.url, headers=headers)
    with urllib.request.urlopen(request) as response:  # noqa: S310 - resolved source URL
        status = getattr(response, "status", response.getcode())
        append = bool(offset and status == 206)
        content_range = response.headers.get("Content-Range") if append else None
        if append and not str(content_range).startswith(f"bytes {offset}-"):
            raise FetchError(f"{part.name}: server resumed at the wrong byte ({content_range})")
        if offset and not append:
            digest = hashlib.sha256()
            offset = 0
        mode = "ab" if append else "wb"
        with partial.open(mode) as output:
            _copy(response, output, digest, progress)

    actual_size = partial.stat().st_size
    actual_hash = digest.hexdigest()
    if actual_size != part.size:
        raise FetchError(f"{part.name}: expected {part.size} bytes, downloaded {actual_size}")
    if actual_hash != part.sha256:
        raise FetchError(
            f"{part.name}: SHA-256 mismatch (expected {part.sha256}, got {actual_hash})"
        )
    os.replace(partial, final)
    return final, True


def _copy(
    source: BinaryIO,
    target: BinaryIO,
    digest: object,
    progress: Callable[[int], None] | None,
) -> None:
    for chunk in iter(lambda: source.read(CHUNK_SIZE), b""):
        target.write(chunk)
        digest.update(chunk)
        if progress is not None:
            progress(len(chunk))


__all__ = ["FetchError", "fetch_part", "sha256_file"]
