"""Convert one local document to Markdown and store it under an Outrage key.

MarkItDown is an optional dependency and is imported only when conversion is
requested.  This keeps importing :mod:`outrage` and running every unrelated
command independent of the document-conversion stack.
"""

from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from . import keys
from .errors import OutrageError
from .store import Store


class IngestError(OutrageError, RuntimeError):
    """A local document could not be converted or safely stored."""


@dataclass(frozen=True, slots=True)
class IngestResult:
    """The facts about one converted document, whether previewed or written."""

    source: Path
    """The absolute, resolved local file converted."""

    key: str
    """The normalized destination key."""

    title: str
    """The title chosen for the document."""

    characters: int
    """The number of Markdown characters produced."""

    format: Literal["markdown"]
    """The stored format, always ``"markdown"``."""

    title_key: str | None
    """The metadata key written for the title, or ``None`` for a dry run."""

    dry_run: bool
    """Whether conversion was performed without writing the document."""


def _local_file(source: str | os.PathLike[str]) -> Path:
    """Resolve ``source`` and refuse anything other than a local regular file."""
    raw = os.fspath(source)
    if not isinstance(raw, str):
        raise TypeError(f"source must resolve to a string path, got {type(raw).__name__}")

    parsed = urlsplit(raw)
    if parsed.scheme and ("://" in raw or parsed.scheme.lower() in {"data", "file"}):
        raise IngestError("ingest-source-url", source=raw)

    try:
        path = Path(raw).expanduser().resolve()
    except (OSError, RuntimeError) as exc:
        raise IngestError("ingest-source-not-file", source=raw, reason=str(exc)) from exc
    if not path.is_file():
        reason = "does not exist" if not path.exists() else "is not a regular file"
        raise IngestError("ingest-source-not-file", source=str(path), reason=reason)
    return path


def available() -> bool:
    """Whether the optional ``documents`` extra is installed.

    A spec lookup rather than an import, because a server asks this while it is
    deciding which tools to register and MarkItDown brings its readers and a
    model runtime with it - a second or more of import for a question about
    whether the answer exists. Consulting :data:`sys.modules` first is part of
    that lookup, so a test that puts ``None`` there is answered the same way an
    absent install is.

    Only whether MarkItDown itself is importable. A reader missing for one
    format is a property of the file being converted, not of the extra, and is
    reported per conversion by :func:`_convert`.
    """
    return importlib.util.find_spec("markitdown") is not None


def _missing_dependency(error: BaseException, missing_type: type[BaseException]) -> bool:
    """Whether a MarkItDown conversion failure wraps a missing parser dependency."""
    attempts = getattr(error, "attempts", None) or ()
    return any(
        attempt.exc_info is not None and isinstance(attempt.exc_info[1], missing_type)
        for attempt in attempts
    )


def _reason(error: BaseException) -> str:
    """One line of converter detail for the one-line front-end rendering."""
    return " ".join(str(error).split())


def _prefer_lf(markdown: str) -> str:
    """Every line ending in converted output as LF.

    **Where there is no line ending to preserve, prefer LF.** A conversion
    *authors* its output rather than
    carrying it, so nothing here is a transfer being converted -- the CRLF
    MarkItDown emits is an artefact of whatever it read, not a property of the
    Markdown it wrote, and one canonical answer beats whatever the source
    happened to use.

    The two real endings only. A lone CR is one, so it is included; the exotic
    endings ``str.splitlines`` also breaks on are out of scope.
    """
    return markdown.replace("\r\n", "\n").replace("\r", "\n")


def _convert(path: Path) -> tuple[str, str | None]:
    """Convert one local file with MarkItDown's built-ins and no plugins."""
    try:
        from markitdown import (
            FileConversionException,
            MarkItDown,
            MarkItDownException,
            MissingDependencyException,
            UnsupportedFormatException,
        )
    except ImportError as exc:
        raise IngestError("ingest-documents-extra-missing") from exc

    converter = MarkItDown(enable_plugins=False)
    try:
        converted: Any = converter.convert_local(path)
    except UnsupportedFormatException as exc:
        raise IngestError("ingest-format-unsupported", source=str(path)) from exc
    except MissingDependencyException as exc:
        raise IngestError(
            "ingest-converter-dependency-missing", source=str(path), reason=_reason(exc)
        ) from exc
    except FileConversionException as exc:
        if _missing_dependency(exc, MissingDependencyException):
            raise IngestError(
                "ingest-converter-dependency-missing", source=str(path), reason=_reason(exc)
            ) from exc
        raise IngestError(
            "ingest-conversion-failed", source=str(path), reason=_reason(exc)
        ) from exc
    except OSError as exc:
        raise IngestError("ingest-source-unreadable", source=str(path), reason=str(exc)) from exc
    except MarkItDownException as exc:
        raise IngestError(
            "ingest-conversion-failed", source=str(path), reason=_reason(exc)
        ) from exc

    markdown = converted.markdown
    if not isinstance(markdown, str):
        raise TypeError(f"MarkItDown returned {type(markdown).__name__} as markdown, not str")
    converted_title = converted.title
    if converted_title is not None and not isinstance(converted_title, str):
        raise TypeError(
            f"MarkItDown returned {type(converted_title).__name__} as title, not str or None"
        )
    return _prefer_lf(markdown), converted_title


def ingest_document(
    store: Store,
    source: str | os.PathLike[str],
    key: str,
    *,
    title: str | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
) -> IngestResult:
    """Convert a local file to Markdown and store it at ``key``.

    Only :meth:`markitdown.MarkItDown.convert_local` is used and converter
    plugins are disabled.  URLs, directories and missing files are refused.
    An existing destination is preserved unless ``overwrite`` is true.
    ``dry_run`` still performs the conversion but writes neither the document
    nor its title.

    The title is selected from the explicit ``title``, MarkItDown's title, and
    finally the source filename stem, in that order.  The source path is
    returned to the caller but is not stored as metadata.
    """
    path = _local_file(source)
    destination = keys.parse(key).key
    destination_title = keys.with_prefix(destination, f"{keys.META_PREFIX}title")
    if (store.exists(destination) or store.exists(destination_title)) and not overwrite:
        raise IngestError("ingest-target-exists", key=destination)
    if title is not None and not isinstance(title, str):
        raise TypeError(f"title must be a string, got {type(title).__name__}")

    markdown, converted_title = _convert(path)
    chosen_title = title if title is not None else converted_title or path.stem
    title_key = None
    if not dry_run:
        destination = store.store_document(
            destination, markdown, format="markdown", title=chosen_title
        )
        title_key = keys.with_prefix(destination, f"{keys.META_PREFIX}title")

    return IngestResult(
        source=path,
        key=destination,
        title=chosen_title,
        characters=len(markdown),
        format="markdown",
        title_key=title_key,
        dry_run=dry_run,
    )


__all__ = ["IngestError", "IngestResult", "available", "ingest_document"]
