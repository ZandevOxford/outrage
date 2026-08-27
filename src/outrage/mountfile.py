"""A mount table kept in a file, and the fiction that makes it one.

A mount table used to be *only* an argument list. For the server that meant it
lived inside a client's ``.mcp.json``, in the ``args`` array, as a flat run of
``--mount ref=reference.sqlite`` strings that could only be changed by editing
JSON belonging to somebody else; for the command line it meant there was no
table at all. This is the file it lives in instead --
``project/reference/planned/mounts/config`` is the whole argument, and the six
calls in it are what the code below implements.

**The one rule to know.** A file behaves as if the equivalent options had been
inserted into the command line at the point where the file is named. The
default file in the store directory is spelled at the very front, so everything
actually typed comes after it and wins; an explicit ``--mount-config FILE``
splices that file's options in where the flag appears, so a flag before it
loses and a flag after it wins.

That rule is worth its weight because it needs no second vocabulary:
precedence, repetition and the interaction of the two are already whatever
argparse does, and there is no separate notion of a merge to specify. It has
one mechanical caveat, and it is unavoidable: ``--dir`` is what *finds* the
default file, so it cannot be resolved by the same pass that consumes it.
Reading is two passes -- :func:`directory_in` settles ``--dir`` from the real
argument list, then :func:`spliced` builds the list argparse actually parses.

**One exception to the fiction, and it is the point of having a file.** A
duplicate mount point is refused within one source and the later one wins
across sources. ``MountedStore`` refuses two mounts at one key because that is
somebody typing a mount point twice on one line; that reason does not carry
across two sources, where replacing one entry of a committed table for a single
maintenance run is the whole intent. So :func:`spliced` drops an earlier mount
point only when a *later* source claims it, and leaves a repeat within one
source exactly where it was, for ``open_mounts`` to refuse as it always did.

**TOML, and read only.** A config file is the one place people want comments,
which JSON has none of, and YAML would have cost a second required runtime
dependency where ``mcp`` is the only one today. ``tomllib`` has been in the
standard library since 3.11 and this package requires 3.14. It reads and does
not write, which is less of a problem than it looks: a file whose reason for
existing is comments should not be machine-rewritten, because a rewrite is
exactly what loses them.
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from . import keys
from . import store as store_module
from .errors import OutrageError
from .mounts import SPEC_DELIMITER, MountError, mount_point, parse_spec

#: The file read from inside ``--dir`` when nobody names one. The table is a
#: property of the store directory it describes, which is also what makes every
#: FILE in it relative to the same place the flags are relative to.
DEFAULT_NAME = "mounts.toml"

#: Names a file explicitly, and splices it in where the flag appears. Spelled
#: ``--mount-config`` rather than ``--config``, which would read as being about
#: the ``outrage config`` subcommand -- that writes an MCP client's JSON, which
#: is a different file for a different reader.
CONFIG_FLAG = "--mount-config"

#: Removes a mount some earlier source declared, which is the one thing an
#: override cannot do: it can replace an entry or add one, and only this takes
#: one away. Command line only -- a file has nothing before it to remove.
UNMOUNT_FLAG = "--unmount"

#: Ignores the default file for one run, so that only what is typed is
#: mounted. The escape ``project/reference/planned/mounts/config`` leaves open,
#: settled the narrow way: it suppresses the file nobody named, and an explicit
#: ``--mount-config`` is something the caller can simply not type. Needed
#: rather than tidy -- a mount table requires a writable root, so without it a
#: project holding a table could not read a packed store at all.
NO_CONFIG_FLAG = "--no-mount-config"

#: The option that says which *directory* the stores are in, and so the one
#: option a file cannot hold: it is what finds the default file.
DIR_FLAG = "--dir"

#: The store answering for every key no mount claims. The command line spells
#: it ``--store`` as well, which is an alias for this and not a second option.
ROOT_FLAG = "--root-mount"

#: Another store, under a mount point.
MOUNT_FLAG = "--mount"

#: The same, with every write routed there refused before it reaches the store.
READ_ONLY_FLAG = "--mount-ro"

#: The flags this module has to recognise in an argument list. Everything else
#: passes through untouched, including ``--store``: it shares a ``dest`` with
#: ``--root-mount`` on the command line, so argparse's own last-one-wins is
#: already the right answer for it and there is nothing here to decide.
_FLAGS = (DIR_FLAG, MOUNT_FLAG, READ_ONLY_FLAG, UNMOUNT_FLAG, CONFIG_FLAG, NO_CONFIG_FLAG)

#: The file's fields are named after the options they stand for, so that
#: nothing here is a new word for anything: a table entry is ``KEY = "FILE"``,
#: which is the ``KEY=FILE`` of a spec with the delimiter turned into TOML's
#: own. This one holds the root mount.
ROOT_FIELD = "root-mount"

#: The ``[mount]`` table: one ``KEY = "FILE"`` entry per read-write mount.
MOUNT_FIELD = "mount"

#: The ``[mount-ro]`` table: the same, read-only.
READ_ONLY_FIELD = "mount-ro"

#: Every field a mount configuration may hold. Anything else in one is refused
#: rather than ignored -- ``--log`` and the rest would splice in for free, and
#: whether the file grows that far is a call to make on purpose.
FIELDS = (ROOT_FIELD, MOUNT_FIELD, READ_ONLY_FIELD)

#: What a command line counts as, against the numbered file sources. Distinct
#: from every file and the same for every token typed, wherever a splice landed
#: between them: two ``--mount ref=`` on one line are one person's mistake even
#: with a ``--mount-config`` written between them.
_TYPED = -1


class MountFileError(OutrageError, ValueError):
    """Raised when a mount configuration file cannot be read as a mount table."""


@dataclass(frozen=True, slots=True)
class MountTable:
    """What one file says, parsed, with every mount point already validated."""

    path: Path
    root: str | None
    """``--root-mount``: the store answering for every key no mount claims."""
    mounts: tuple[tuple[str, str], ...]
    """``(mount point, file)`` pairs, mounted read-write."""
    read_only: tuple[tuple[str, str], ...]
    """The same, mounted read-only."""

    def options(self) -> list[str]:
        """This table as the command line it stands for."""
        return [token for item in _items(self, _TYPED) for token in item.tokens]


@dataclass(frozen=True, slots=True)
class _Item:
    """One option and its value, and which source put it there.

    Held together rather than as loose tokens so that dropping an overridden
    mount cannot leave its value behind as a stray positional -- which is how
    the same option would be read if the flag in front of it disappeared.
    """

    source: int
    tokens: list[str]
    mount: str | None
    """The mount point this claims, when it is a mount at all."""
    removes: bool = False
    """Whether it claims that point in order to *unmount* it.

    Such an item contributes no tokens: what it does happens here, by taking
    the earlier ones away.
    """


def read(path: str | os.PathLike[str]) -> MountTable:
    """Read one mount configuration file.

    Every refusal a mount point can earn is reached through
    :func:`outrage.mounts.mount_point`, which is the same parse ``--mount``
    goes through, rather than being written a second time here. A file that
    grew its own idea of what a key is would be a second grammar, and the
    project has one.
    """
    path = Path(path).expanduser()
    try:
        with open(path, "rb") as handle:
            loaded = tomllib.load(handle)
    except FileNotFoundError as exc:
        # Only a file somebody named reaches this: the default one is tested
        # for before it is read, because not having one is the ordinary case.
        raise MountFileError("mount-config-missing", path=str(path)) from exc
    except OSError as exc:
        raise MountFileError("mount-config-unreadable", path=str(path), reason=str(exc)) from exc
    except tomllib.TOMLDecodeError as exc:
        raise MountFileError("mount-config-not-toml", path=str(path), reason=str(exc)) from exc

    unknown = sorted(set(loaded) - set(FIELDS))
    if unknown:
        # Refused rather than ignored. A file exists to be read later by
        # somebody who is not watching, and a field silently doing nothing is
        # the failure a mount configuration is least able to notice: a mount
        # that is simply absent reads as a store that is simply empty.
        raise MountFileError(
            "mount-config-unknown-field", path=str(path), fields=unknown, known=list(FIELDS)
        )

    root = loaded.get(ROOT_FIELD)
    if root is not None and not isinstance(root, str):
        raise MountFileError(
            "mount-config-not-a-file",
            path=str(path),
            field=ROOT_FIELD,
            got=type(root).__name__,
        )

    table = MountTable(
        path=path,
        root=root,
        mounts=_entries(loaded, MOUNT_FIELD, path),
        read_only=_entries(loaded, READ_ONLY_FIELD, path),
    )
    seen: set[str] = set()
    for point, _ in (*table.mounts, *table.read_only):
        # TOML refuses a repeated key within one table itself, so this is only
        # ever the same mount point in `mount` and in `mount-ro` - which is the
        # same collision, since the two share one namespace.
        if point in seen:
            raise MountFileError("mount-config-duplicate", path=str(path), mount=point)
        seen.add(point)
    return table


def _entries(loaded: dict[str, object], field: str, path: Path) -> tuple[tuple[str, str], ...]:
    """One ``[mount]``-shaped table, as validated ``(mount point, file)`` pairs."""
    section = loaded.get(field, {})
    if not isinstance(section, dict):
        raise MountFileError(
            "mount-config-not-a-table", path=str(path), field=field, got=type(section).__name__
        )
    entries = []
    for point, file in section.items():
        if not isinstance(file, str):
            raise MountFileError(
                "mount-config-not-a-file",
                path=str(path),
                field=f"{field}.{point}",
                got=type(file).__name__,
            )
        if SPEC_DELIMITER in point:
            # A mount point holding the delimiter has no `--mount` spelling,
            # and the file is defined as the options it stands for. Refused
            # here rather than rendered into a spec that would split somewhere
            # else and mount a different key.
            raise MountFileError(
                "mount-config-unspellable",
                path=str(path),
                mount=point,
                delimiter=SPEC_DELIMITER,
            )
        entries.append((mount_point(point), file))
    return tuple(entries)


def directory_in(argv: Sequence[str]) -> str | None:
    """``--dir`` as the argument list gives it, or None.

    The first of the two passes. It cannot be argparse's, because the parser
    that would answer this is the one being handed a list that does not exist
    until the answer is known.
    """
    found = None
    index = 0
    while index < len(argv):
        token = argv[index]
        flag, delimiter, inline = token.partition("=")
        if token.startswith("-") and _canonical(flag) == DIR_FLAG:
            if delimiter:
                found = inline
            elif index + 1 < len(argv):
                found = argv[index + 1]
                index += 1
        index += 1
    return found


def spliced(
    argv: Sequence[str],
    *,
    directory: str | os.PathLike[str] | None = None,
    front: int = 0,
) -> list[str]:
    """``argv`` with every mount configuration file's options written into it.

    The list argparse is then given. ``directory`` is the store directory to
    look for the default file in; omitted, it is whatever ``--dir`` in ``argv``
    says, then the environment, then the working directory -- the same answer
    the command itself will resolve.

    ``front`` is how many leading tokens the default file's options go *after*,
    and is the one place the fiction needs a number. "The very front" is where
    they belong, so that everything typed comes after them and wins -- but a
    command line with subcommands has no such position at the front: an option
    belonging to ``outrage ls`` written before the word ``ls`` is an option on
    the wrong parser. So the front of the line is the front of the subcommand,
    and a front-end that has one says where it is.

    An explicit file *stacks* on the default one rather than replacing it,
    because that is what the splice rule says when read literally: naming a
    file inserts its options, and inserting them says nothing about the ones
    already there. Whether an escape from the default file is wanted is left
    open in ``project/reference/planned/mounts/config``.
    """
    base = store_module.resolve_directory(
        directory if directory is not None else directory_in(argv)
    )
    items: list[_Item] = list(_typed(argv[:front]))
    source = 0
    default = base / DEFAULT_NAME
    if default.is_file() and not _suppressed(argv):
        items += _items(read(default), source)
        source += 1
    for item in _typed(argv[front:]):
        if item.mount is None and item.tokens[0] == CONFIG_FLAG:
            items += _items(read(item.tokens[1]), source)
            source += 1
        else:
            items.append(item)
    return [token for item in _overridden(items) for token in item.tokens]


def _typed(argv: Sequence[str]) -> Iterator[_Item]:
    """An argument list as items, with the options this module knows named.

    Every other token passes through one at a time and untouched, so an option
    nothing here has heard of -- one a newer release added, one a subcommand
    owns -- is neither reordered nor examined.
    """
    index = 0
    while index < len(argv):
        token = argv[index]
        flag, delimiter, inline = token.partition("=")
        canonical = _canonical(flag) if token.startswith("-") else None
        if canonical == NO_CONFIG_FLAG:
            # Consumed here: it says which files are read, which is a question
            # already answered by the time a parser sees the list.
            index += 1
            continue
        if canonical in (MOUNT_FLAG, READ_ONLY_FLAG, UNMOUNT_FLAG, CONFIG_FLAG):
            if delimiter:
                value = inline
            elif index + 1 < len(argv):
                value = argv[index + 1]
                index += 1
            else:
                # A flag with nothing after it. Passed through as it was
                # written, so argparse says so in its own words rather than
                # this raising a second sentence about the same mistake.
                yield _Item(_TYPED, [token], None)
                index += 1
                continue
            if canonical == CONFIG_FLAG:
                yield _Item(_TYPED, [canonical, value], None)
            elif canonical == UNMOUNT_FLAG:
                # A key, not a spec: there is no file to name in taking one
                # away. Parsed the same way a mount point is, so that
                # ``--unmount /ref/`` names what ``--mount ref=`` mounted --
                # except at the root, which has its own sentence because
                # ``mount_point`` would answer it as a *mount* missing its
                # point, and nothing here is missing.
                if keys.parse(value).key == keys.ROOT:
                    raise MountError("mount-unmount-at-root")
                yield _Item(_TYPED, [], mount_point(value), removes=True)
            else:
                yield _Item(_TYPED, [canonical, value], parse_spec(value)[0])
        else:
            yield _Item(_TYPED, [token], None)
        index += 1


def _suppressed(argv: Sequence[str]) -> bool:
    """Whether the default file is to be ignored for this run."""
    return any(
        token.startswith("-") and _canonical(token.partition("=")[0]) == NO_CONFIG_FLAG
        for token in argv
    )


def _items(table: MountTable, source: int) -> list[_Item]:
    """One file's table as the options it stands for, in order."""
    items = []
    if table.root is not None:
        items.append(_Item(source, [ROOT_FLAG, table.root], None))
    for flag, entries in ((MOUNT_FLAG, table.mounts), (READ_ONLY_FLAG, table.read_only)):
        for point, file in entries:
            items.append(_Item(source, [flag, f"{point}{SPEC_DELIMITER}{file}"], point))
    return items


def _overridden(items: Sequence[_Item]) -> list[_Item]:
    """Drop each mount a later claim replaces or removes, and keep the rest.

    The whole of what a file changes about duplicate handling, in one pass. A
    mount point claimed again from somewhere else is an override and the
    earlier one goes; claimed again from the same place it is a mistake, and it
    survives to be refused by ``MountedStore`` with the sentence it has always
    had.

    **An unmount is not a claim of that kind and does not follow that rule.**
    It is a deletion, so it takes away every earlier mount at that point
    whatever source they came from -- including the command line it was typed
    on, where two ``--mount`` at one key would have been the mistake the rule
    exists to catch and ``--mount ref=... --unmount ref`` plainly is not. A
    ``--mount`` written *after* it mounts again, which is the ordering rule
    doing its usual work and needs nothing said about it.

    An unmount that removed nothing is refused. The same argument
    ``--mount-ro`` makes by refusing an unmatched mount point: it reads as
    though it worked, and what is left behind is the mount somebody meant to
    take away.
    """
    last: dict[str, int] = {}
    for index, item in enumerate(items):
        if item.mount is not None:
            last[item.mount] = index
    kept = []
    for index, item in enumerate(items):
        if item.mount is not None:
            winner = items[last[item.mount]]
            if index != last[item.mount] and (winner.removes or item.source != winner.source):
                continue
            if item.removes:
                if not any(
                    other.mount == item.mount and not other.removes for other in items[:index]
                ):
                    raise MountError("mount-unmount-unmatched", mount=item.mount)
                continue
        kept.append(item)
    return kept


def _canonical(flag: str) -> str | None:
    """The option ``flag`` names, spelled in full, or None for anything else.

    Abbreviations are resolved the way argparse resolves them -- an exact match
    first, then a unique prefix -- because the two have to agree about which
    tokens are mounts. They would not otherwise: an abbreviated ``--mount``
    this pass failed to see would keep a mount the command line meant to
    override, and the run would fail on a duplicate instead of doing what was
    asked.
    """
    if not flag.startswith("--") or len(flag) < 3:
        return None
    # The constant, never the token: what comes back is compared against these
    # names, and a string equal to one of them is not the same object as it.
    matches = [known for known in _FLAGS if known == flag] or [
        known for known in _FLAGS if known.startswith(flag)
    ]
    return matches[0] if len(matches) == 1 else None


__all__ = [
    "CONFIG_FLAG",
    "DEFAULT_NAME",
    "DIR_FLAG",
    "FIELDS",
    "MOUNT_FIELD",
    "MOUNT_FLAG",
    "NO_CONFIG_FLAG",
    "READ_ONLY_FIELD",
    "READ_ONLY_FLAG",
    "ROOT_FIELD",
    "ROOT_FLAG",
    "UNMOUNT_FLAG",
    "MountFileError",
    "MountTable",
    "directory_in",
    "read",
    "spliced",
]
