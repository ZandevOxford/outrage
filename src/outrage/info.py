"""What the process answering is: its environment, its stores, and its log.

A caller reaching a store through the MCP server can see everything in it and
nothing about the server holding it. That is a real gap rather than a cosmetic
one, because the answers are not guessable from outside: which Python
environment this build runs in, which files the mounts are kept in, and which
configuration file a mount would be edited in.

**The environment is the one worth stating.** An installation is normally
editable, so the working tree *is* the build, and a caller that wants to run
the command line has to run the one beside *this* interpreter rather than
whatever ``outrage`` resolves to on their PATH. :func:`describe` reports the
interpreter, its prefix and the console script's absolute path so that it can.

Facts only, in the dataclasses below, and no sentence anywhere: both front ends
call :func:`describe` and each says what it says. The report is about the
process that answers it -- a command line run has no event log of its own and
reports none, which is not a claim about what the server for the same store
does.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from . import __version__, config, eventlog, keys
from . import mounts as mounts_module
from . import store as store_module
from .eventlog import EventLog
from .store import Store


@dataclass(frozen=True, slots=True)
class MountInfo:
    """One mount, as a report names it."""

    mount: str
    """The mount point written for a person to read; the root is ``/``."""

    path: str | None
    """Absolute path of the file this store is kept in, or None for a store
    that keeps none. Absolute because the point of reporting it is that
    somebody elsewhere can act on it."""

    kind: str
    """:data:`~outrage.mounts.ROOT_KIND`, :data:`~outrage.mounts.MOUNT_KIND` or
    :data:`~outrage.mounts.READ_ONLY_MOUNT_KIND`."""

    read_only: bool
    """Whether this process refuses writes routed here."""


@dataclass(frozen=True, slots=True)
class Info:
    """What one running front end can say about itself."""

    version: str
    python: str
    """The running interpreter, as :data:`sys.executable` gives it.

    **Not resolved through its symlinks**, unlike every path below. A virtual
    environment's interpreter is a link to the one it was made from, so
    resolving it would name the environment the caller must *not* use."""

    prefix: str
    """The environment the interpreter belongs to, :data:`sys.prefix`."""

    command: tuple[str, ...] = ()
    """The command line entry point in that environment, empty when this
    installation has no console script -- see
    :func:`outrage.config.script_command`."""

    directory: str | None = None
    """The store directory, or None when the caller had none to give. None
    rather than the default guess: a report that names the wrong directory
    confidently is worse than one that says it does not know."""

    mount_config: tuple[str, ...] = ()
    """The mount configuration files read, in the order they were read."""

    log: str | None = None
    """Where this process is recording what it does, or None when it is not."""

    log_content: str | None = None
    """How much document text that log keeps, or None when there is no log."""

    mounts: tuple[MountInfo, ...] = ()
    """The stores behind the namespace, as they were opened."""


def describe(
    opened: Store,
    *,
    directory: str | os.PathLike[str] | None = None,
    mount_config: Sequence[str] = (),
    log: EventLog | None = None,
) -> Info:
    """Describe this process and the stores it has open.

    ``opened`` is reported as it **is**, not as it was asked for: the mounts
    come from the live table, so a mount that was overridden, or one that
    arrived without being named on any command line, is in the answer once and
    where it really is. A lone store that is not a table is the root of a
    namespace of one, which is what it answers as.

    ``mount_config`` and ``directory`` are the two things the stores cannot be
    asked -- :func:`outrage.mountfile.sources` and
    :func:`outrage.store.resolve_directory` know them, and by the time there is
    a table both have been flattened away.
    """
    log = log if log is not None else eventlog.NULL
    return Info(
        version=__version__,
        # Deliberately unresolved; see the attribute.
        python=sys.executable,
        prefix=sys.prefix,
        command=tuple(config.script_command(config.CLI_SCRIPT_NAME) or ()),
        directory=None if directory is None else _absolute(directory),
        mount_config=tuple(_absolute(path) for path in mount_config),
        log=_absolute(log.path) if log.enabled and log.path is not None else None,
        log_content=log.content if log.enabled else None,
        mounts=mount_infos(opened),
    )


def mount_infos(opened: Store) -> tuple[MountInfo, ...]:
    """Every mount behind ``opened``, or the one store when it is not a table.

    A :class:`~outrage.mounts.Mount` is made for the lone store rather than a
    table of one, because a table refuses a root that will not take writes and
    describing a store must not fail where reading it succeeds.

    Public because the mount tools answer with the table as it now is, and a
    second projection of a mount into a report is a second place for the two to
    disagree about what a mount point is called.
    """
    if isinstance(opened, mounts_module.MountedStore):
        return tuple(_mount(mount) for mount in opened)
    return (_mount(mounts_module.Mount(keys.ROOT, opened)),)


def _mount(mount: mounts_module.Mount) -> MountInfo:
    """One mount as a report names it."""
    return MountInfo(
        mount=mount.name,
        path=(
            _absolute(mount.store.path) if isinstance(mount.store, store_module.FileStore) else None
        ),
        kind=mounts_module.ROOT_KIND if mount.is_root else mount.kind,
        read_only=mount.read_only,
    )


def _absolute(path: str | os.PathLike[str]) -> str:
    """A path as somewhere else can act on it.

    ``--dir`` may be relative and usually is, so every path in a report is
    resolved against the working directory this process was started in -- which
    is the one thing a reader of the report has no way to recover.
    """
    return str(Path(path).expanduser().resolve())


__all__ = [
    "Info",
    "MountInfo",
    "describe",
    "mount_infos",
]
