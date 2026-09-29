"""The writable document store shared by every project for one user.

This store is deliberately outside a project's store directory.  It is a
built-in mount rather than an ordinary mount specification, so the rule that
keeps every configured store path relative to ``--dir`` remains intact.

The same directory holds the user's configuration file, ``config.toml``. It is
named for Outrage as a whole rather than for any one feature, because a file
already on people's machines is expensive to rename, and each feature reads
its own table from it.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

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
#: The user's configuration file, beside the home store.
CONFIG_FILE = "config.toml"
#: Permission bits that must be clear on the configuration file: any access
#: at all by group or others, as libpq requires of ``.pgpass``.
CONFIG_EXPOSED_BITS = 0o077
#: The bootstrap document's key inside the home store.
README_KEY = "readme"
#: The bootstrap document's title metadata.
README_TITLE = "Home store"
#: The shipped template used to bootstrap the home store.
README_DOCUMENT = "home_readme"


class HomeStoreError(OutrageError, OSError):
    """Raised when the built-in home store cannot be opened or bootstrapped."""


class UserConfigError(OutrageError, ValueError):
    """Raised when the user's configuration file cannot be used."""


def path() -> Path:
    """The user-wide store file, independent of project directory settings."""
    return Path.home() / DIRECTORY_NAME / STORE_FILE


def config_path() -> Path:
    """The user's configuration file, which need not exist."""
    return Path.home() / DIRECTORY_NAME / CONFIG_FILE


def read_config(path: Path | None = None) -> dict[str, Any]:
    """The user's configuration as a table, or an empty one when there is no file.

    **A file other users can open is refused before it is read**, since it may
    hold an API key, and a key readable by others has to be treated as out.
    Refusing says so; ignoring the file instead would leave its owner puzzled
    about why their settings had no effect. Any group or other access counts,
    writing included, as a key that others can redirect is as bad as one they
    can read. POSIX only: Windows permissions are not mode bits.
    """
    path = config_path() if path is None else path
    try:
        if os.name == "posix":
            mode = path.stat().st_mode & 0o7777
            if mode & CONFIG_EXPOSED_BITS:
                raise UserConfigError("user-config-exposed", path=str(path), mode=f"{mode:o}")
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeDecodeError) as exc:
        raise UserConfigError("user-config-unreadable", path=str(path), reason=str(exc)) from exc
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise UserConfigError("user-config-not-toml", path=str(path), reason=str(exc)) from exc


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
    "CONFIG_EXPOSED_BITS",
    "CONFIG_FILE",
    "DIRECTORY_NAME",
    "HomeStoreError",
    "MOUNT_POINT",
    "README_DOCUMENT",
    "README_KEY",
    "README_TITLE",
    "STORE_FILE",
    "UserConfigError",
    "config_path",
    "open_store",
    "path",
    "read_config",
    "readme",
]
