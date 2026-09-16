"""The writable document store shared by every project for one user.

This store is deliberately outside a project's store directory.  It is a
built-in mount rather than an ordinary mount specification, so the rule that
keeps every configured store path relative to ``--dir`` remains intact.
"""

from __future__ import annotations

from pathlib import Path

from . import shipped
from .errors import OutrageError
from .eventlog import EventLog
from .store import Store
from .store_sqlite import SqliteStore

#: The namespace prefix where the user-wide store is mounted.
MOUNT_POINT = "home"
#: The directory beneath the user's home that holds Outrage state.
DIRECTORY_NAME = ".outrage"
#: The distinct file name that cannot alias a project root store.
STORE_FILE = "home.sqlite"
#: The bootstrap document's key inside the home store.
README_KEY = "readme"
#: The bootstrap document's title metadata.
README_TITLE = "Home store"
#: The shipped template used to bootstrap the home store.
README_DOCUMENT = "home_readme"


class HomeStoreError(OutrageError, OSError):
    """Raised when the built-in home store cannot be opened or bootstrapped."""


def path() -> Path:
    """The user-wide store file, independent of project directory settings."""
    return Path.home() / DIRECTORY_NAME / STORE_FILE


def readme() -> str:
    """The shipped home-store conventions used for a new store's readme."""
    return shipped.document_text(README_DOCUMENT)


def open_store(
    *,
    log: EventLog | None = None,
    mount_point: str = MOUNT_POINT,
    versioning: bool = True,
) -> Store:
    """Open the home store and seed its minimal readme when it is empty."""
    database = path()
    opened: SqliteStore | None = None
    try:
        opened = SqliteStore(
            database.parent,
            filename=database.name,
            log=log,
            mount_point=mount_point,
            versioning=versioning,
        )
        if not opened.exists(README_KEY) and opened.get_documents(limit=1).total == 0:
            opened.store_document(
                README_KEY,
                readme(),
                "markdown",
                title=README_TITLE,
            )
        return opened
    except Exception as exc:
        if opened is not None:
            opened.close()
        raise HomeStoreError("home-store-open-failed", path=str(database), cause=str(exc)) from exc


__all__ = [
    "DIRECTORY_NAME",
    "HomeStoreError",
    "MOUNT_POINT",
    "README_DOCUMENT",
    "README_KEY",
    "README_TITLE",
    "STORE_FILE",
    "open_store",
    "path",
    "readme",
]
