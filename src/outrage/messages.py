"""Turning a :class:`~outrage.errors.OutrageError` into a sentence for a person.

The one place wording lives. The layers that *raise* carry facts and a code
(see :mod:`outrage.errors`); this renders them, and the front end says how a key
should be named.

**Why the naming is a parameter.** There are two front ends and the right name
for a key differs between them. The command line opens one store directory and
knows nothing about a mount table, so a key it failed on is called exactly what
the store calls it. The MCP server presents one namespace across several
stores, so the same key has a longer name there -- ``python/nope`` inside the
store mounted at ``ref`` is ``ref/python/nope`` to any caller. A sentence built
where the failure happened is wrong for one of them and there is no third
answer, which is the defect recorded in
``project/reference/planned/error-naming``.

So ``name`` is a function from the key the raising layer used to the key the
reader should see. It defaults to :func:`outrage.keys.displayed`, which is the
right answer for a single store and spells the root ``/`` rather than as the
empty string that reads like a missing value.

Wording is shared rather than written per front end. Two copies of the same
sentence drift, and the drift is invisible until somebody compares them.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Any

from . import keys
from .errors import OutrageError

#: How a key is named when nobody says otherwise: as one store sees it.
Namer = Callable[[str], str]

#: Every code, and the sentence it renders to. One flat table keyed by code
#: rather than by exception class, because the class says what *kind* of
#: failure it is and the code says which one -- nine different things are an
#: ``InvalidKeyError`` and each has its own explanation.
#:
#: Each entry takes the namer **positionally** and the details by keyword.
#: Positional-only for the namer is what lets a detail be called ``name`` --
#: ``assets-missing`` has one -- without colliding with it. Missing a detail raises
#: ``KeyError`` here, loudly, rather than rendering a sentence with a hole in
#: it, and ``test_messages.py`` pins that every code raised anywhere has an
#: entry and every entry is raised somewhere.
_TEMPLATES: dict[str, Callable[..., str]] = {}


def template(code: str) -> Callable[[Callable[..., str]], Callable[..., str]]:
    """Register the sentence for ``code``."""

    def register(function: Callable[..., str]) -> Callable[..., str]:
        if code in _TEMPLATES:  # pragma: no cover - a duplicate is a bug, not a case
            raise AssertionError(f"two templates for {code!r}")
        _TEMPLATES[code] = function
        return function

    return register


def render(error: OutrageError, name: Namer | None = None) -> str:
    """``error`` as one line, with keys named the way ``name`` says.

    Front ends call this; nothing else should. A code with no template is a
    programming error and raises rather than falling back on something
    plausible -- a message that silently degrades is how a caller ends up
    reading a sentence that is not about their problem.
    """
    try:
        write = _TEMPLATES[error.code]
    except KeyError:  # pragma: no cover - guarded by test_messages
        raise AssertionError(f"no message template for {error.code!r}") from None
    return write(name or keys.displayed, **error.details)


def codes() -> Mapping[str, Callable[..., str]]:
    """The whole table, for the test that checks it against the raise sites."""
    return dict(_TEMPLATES)


# -- store: reading --------------------------------------------------------


@template("key-not-found")
def _key_not_found(name: Namer, /, *, key: str, **_: Any) -> str:
    return f"nothing is stored at or below {name(key)!r}"


@template("key-is-a-container")
def _key_is_a_container(name: Namer, /, *, key: str, beneath: int, **_: Any) -> str:
    # The advice has to name the outer key too. Following it with the inner one
    # asks the store *above* the mount, which holds nothing there -- so the
    # caller gets an empty listing rather than an error and concludes the keys
    # do not exist. That was the worst of the three faults in `error-naming`.
    return (
        f"no content stored at {name(key)!r}, but {beneath} key(s) lie beneath it; "
        f"use list_keys or get_documents to see them"
    )


@template("pattern-not-found")
def _pattern_not_found(
    name: Namer, /, *, key: str, pattern: str, occurrence: int, offset: int, **_: Any
) -> str:
    return (
        f"{pattern!r} does not occur {occurrence + 1} time(s) in {name(key)!r} "
        f"at or after offset {offset}"
    )


@template("pattern-empty")
def _pattern_empty(name: Namer, /, **_: Any) -> str:
    return "a pattern must not be empty; omit it to read from the offset instead"


# -- store: arguments in transit -------------------------------------------
#
# What ``json-string`` exists to catch, said to the caller who can act on it.
# A model that emitted its own closing scaffolding into a value has to be told
# to send the call again, and told what shape the value should have had; the
# sentence is the entire mechanism, so it is the one thing that must not be
# swallowed.


@template("encoding-not-a-json-string")
def _encoding_not_a_json_string(
    name: Namer, /, *, what: str, encoding: str, reason: str, **_: Any
) -> str:
    return (
        f"{what} is not a valid JSON string literal under encoding {encoding!r}: "
        f"{reason}. Send it as a JSON string, quotes included, with nothing after "
        f"the closing quote."
    )


@template("encoding-not-a-string")
def _encoding_not_a_string(
    name: Namer, /, *, what: str, encoding: str, decoded: str, **_: Any
) -> str:
    return (
        f"{what} decoded to {decoded} under encoding {encoding!r}, not a string. "
        f"Send a JSON string literal, not an object or an array."
    )


# -- store: the store file -------------------------------------------------


@template("store-file-unnamed")
def _store_file_unnamed(name: Namer, /, **_: Any) -> str:
    return "a store file needs a name"


@template("store-file-absolute")
def _store_file_absolute(name: Namer, /, *, filename: str, **_: Any) -> str:
    return (
        f"store file {filename!r} is an absolute path; it names a file "
        f"relative to the store directory, so pass the directory as --dir "
        f"and the file alone here"
    )


@template("store-file-escapes")
def _store_file_escapes(name: Namer, /, *, filename: str, **_: Any) -> str:
    return f"store file {filename!r} climbs out of the store directory with '..'"


# -- store: backup ---------------------------------------------------------


@template("backup-unwritable")
def _backup_unwritable(name: Namer, /, *, target: str, reason: str, **_: Any) -> str:
    return f"could not write {target}: {reason}"


@template("backup-is-the-store")
def _backup_is_the_store(name: Namer, /, *, target: str, **_: Any) -> str:
    return f"{target} is the store itself, not a backup of it"


@template("backup-exists")
def _backup_exists(name: Namer, /, *, target: str, **_: Any) -> str:
    return f"{target} already exists; pass overwrite to replace it"


@template("backup-corrupt")
def _backup_corrupt(name: Namer, /, *, target: str, integrity: str, **_: Any) -> str:
    return f"{target} failed its integrity check: {integrity}"


@template("backup-schema-mismatch")
def _backup_schema_mismatch(
    name: Namer, /, *, target: str, found: int, expected: int, **_: Any
) -> str:
    return f"{target} came out at schema {found}, but the store is at {expected}"


@template("backup-incomplete")
def _backup_incomplete(name: Namer, /, *, target: str, differs: str, **_: Any) -> str:
    return (
        f"{target} does not hold what the store holds: {differs}. A concurrent "
        f"write can cause this, so try again before suspecting the copy"
    )


@template("backup-short")
def _backup_short(name: Namer, /, *, target: str, found: int, expected: int, **_: Any) -> str:
    return (
        f"{target} holds {found} documents but the store holds {expected}; "
        f"a concurrent write can cause this, so try again before suspecting the copy"
    )


# -- keys ------------------------------------------------------------------
#
# These name the key **as it was typed**, and deliberately do not put it
# through the namer. Two reasons, and both matter. A key that failed
# validation may not survive being renamed at all -- `mount.outer` parses, so
# rendering the message could raise the very error it is reporting, and an
# error path that fails is the worst one there is. And an invalid key is
# echoed so the caller can compare it against what they sent; a tidied or
# re-prefixed version is a worse answer to "what did I get wrong".
#
# A front end that validates before descending sees the outer spelling here
# anyway, because the outer key is the one it parsed.


@template("key-not-a-string")
def _key_not_a_string(name: Namer, /, *, got: str, **_: Any) -> str:
    return f"key must be a string, got {got}"


@template("key-too-many-segments")
def _key_too_many_segments(name: Namer, /, *, key: str, segments: int, limit: int, **_: Any) -> str:
    return f"key {key!r} has {segments} segments; at most {limit} are allowed"


@template("key-wildcard-not-allowed")
def _key_wildcard_not_allowed(name: Namer, /, *, key: str, **_: Any) -> str:
    return f"key {key!r} may not contain {keys.WILDCARD!r}; it is allowed only when storing"


@template("key-multiple-wildcards")
def _key_multiple_wildcards(name: Namer, /, *, key: str, **_: Any) -> str:
    return f"key {key!r} has more than one {keys.WILDCARD!r} segment"


@template("key-empty-metadata-name")
def _key_empty_metadata_name(name: Namer, /, *, key: str, **_: Any) -> str:
    return f"key {key!r} has no metadata name after {keys.META_PREFIX!r}"


@template("key-segment-too-long")
def _key_segment_too_long(name: Namer, /, *, key: str, what: str, length: int, **_: Any) -> str:
    return (
        f"{what} in key {key!r} is {length} characters; "
        f"at most {keys.MAX_SEGMENT_CHARS} are allowed"
    )


@template("key-segment-bad-character")
def _key_segment_bad_character(
    name: Namer, /, *, key: str, what: str, segment: str, character: str, **_: Any
) -> str:
    return (
        f"{what} {segment!r} in key {key!r} is not valid: it contains "
        f"{character!r}, and a segment may not hold characters below "
        f"{keys.MIN_SEGMENT_CHAR!r}"
    )


@template("key-reserved-segment")
def _key_reserved_segment(name: Namer, /, *, key: str, segment: str, **_: Any) -> str:
    return (
        f"segment {segment!r} in key {key!r} is reserved: a segment beginning "
        f"with {keys.RESERVED_PREFIX!r} names a filter or an operation, and "
        f"{', '.join(sorted(repr(s) for s in keys.RESERVED_SEGMENTS))} are the "
        f"only ones defined"
    )


@template("key-last-not-allowed")
def _key_last_not_allowed(name: Namer, /, *, key: str, **_: Any) -> str:
    return (
        f"key {key!r} may not contain {keys.LAST!r} here; it is resolved "
        f"against the store before a key is parsed"
    )


@template("key-not-below-scope")
def _key_not_below_scope(name: Namer, /, *, key: str, scope: str, **_: Any) -> str:
    return (
        f"key {name(key)} is not at or below {name(scope)}, so it has no "
        f"reading from there"
    )


@template("key-no-last-child")
def _key_no_last_child(name: Namer, /, *, key: str, parent: str, **_: Any) -> str:
    return (
        f"key {key!r} asks for the last key below {name(parent)}, "
        f"which has nothing below it"
    )


@template("key-no-wildcard-to-substitute")
def _key_no_wildcard_to_substitute(name: Namer, /, *, key: str, **_: Any) -> str:
    return f"key {key!r} has no {keys.WILDCARD!r} segment to substitute"


# -- a store kept as files -------------------------------------------------


@template("files-not-text")
def _files_not_text(name: Namer, /, *, key: str, path: str, **_: Any) -> str:
    return (
        f"key {name(key)!r} is the file {path!r}, which does not hold UTF-8 "
        f"text: a store holds text, and this is reported rather than mangled "
        f"into some"
    )


# -- bulk import and export ------------------------------------------------


@template("key-escapes-tree")
def _key_escapes_tree(name: Namer, /, *, key: str, path: str, **_: Any) -> str:
    return (
        f"key {name(key)!r} would be written to {path!r}, which is outside the "
        f"directory it was given: a link along the path leads out of the tree"
    )


@template("key-is-a-symlink")
def _key_is_a_symlink(name: Namer, /, *, key: str, path: str, **_: Any) -> str:
    return (
        f"key {name(key)!r} would be written to {path!r}, which is a symbolic "
        f"link: a link is not a document here, so writing through it would "
        f"replace something this store never held"
    )


@template("key-segment-is-traversal")
def _key_segment_is_traversal(name: Namer, /, *, key: str, segment: str, **_: Any) -> str:
    return (
        f"key {name(key)!r} has a segment of {segment!r}, which is a legal "
        f"segment and not a path component: it would name a file "
        f"outside the directory being written"
    )


@template("import-source-missing")
def _import_source_missing(name: Namer, /, *, source: str, **_: Any) -> str:
    return f"no directory at {source}"


@template("import-file-missing")
def _import_file_missing(
    name: Namer, /, *, key: str, path: str, given: str, root: str, **_: Any
) -> str:
    missing = f"nothing to store at {name(key)!r}: no file at {path}"
    if os.path.isabs(given):
        return missing
    # A relative path is taken from the export directory, not from wherever the
    # caller is standing, and the joined result is the only thing this sentence
    # would otherwise show: `.outrage/export/x.md` typed at the repository root
    # is reported missing from `.../.outrage/export/.outrage/export/x.md`, and
    # the doubled segment reads as a bug in the tool rather than as a path
    # taken from somewhere else. Naming the directory is what makes it read as
    # what it is. `context/66/state`.
    return f"{missing} - {given!r} is relative to the export directory {root}"


@template("import-file-escapes-tree")
def _import_file_escapes_tree(name: Namer, /, *, key: str, path: str, **_: Any) -> str:
    return (
        f"nothing to store at {name(key)!r}: the file at {path} is outside the "
        f"export directory, and only a file exported into it can be stored back"
    )


# -- mounts ----------------------------------------------------------------
#
# A mount point is named with `keys.displayed` directly rather than through the
# namer. These are raised while a table is being *built*, or about the table
# itself, so a prefix is already the name the whole namespace uses -- putting
# it through a namer would prefix it a second time.


@template("mount-key-too-deep")
def _mount_key_too_deep(name: Namer, /, *, key: str, mount: str, **_: Any) -> str:
    return (
        f"{keys.displayed(key)!r} in the store mounted at {keys.displayed(mount)!r} has no "
        f"name in this namespace: joined it exceeds "
        f"{keys.MAX_JOINED_SEGMENTS} segments. The store holds a key deeper "
        f"than {keys.MAX_SEGMENTS} segments, which `outrage check` reports; it "
        f"predates that bound and has to be moved before the store can be "
        f"mounted here."
    )


@template("mount-read-only")
def _mount_read_only(name: Namer, /, *, key: str, mount: str, action: str, **_: Any) -> str:
    return (
        f"cannot {action} {keys.displayed(key)!r}: the store mounted at "
        f"{keys.displayed(mount)!r} is read-only. Either --mount-ro says so, and "
        f"--mount instead allows changes here; or it is a store nothing can "
        f"write - a packed parquet one, or the documentation shipped inside "
        f"outrage, which the next upgrade would replace."
    )


@template("mount-root-read-only")
def _mount_root_read_only(name: Namer, /, **_: Any) -> str:
    return (
        "the store at the root cannot be mounted read-only: it is the one "
        "--dir names, and it owns every key no mount claims"
    )


@template("mount-root-not-writable")
def _mount_root_not_writable(name: Namer, /, *, backend: str, **_: Any) -> str:
    return (
        f"the store at the root is a {backend}, which cannot be written: the "
        f"root owns every key no mount claims, so nothing would have anywhere "
        f"to go. Mount it at a prefix with --mount-ro, or open it directly to "
        f"read it."
    )


@template("mount-point-is-metadata")
def _mount_point_is_metadata(name: Namer, /, *, mount: str, **_: Any) -> str:
    return (
        f"cannot mount at {keys.displayed(mount)!r}: a mount point may not "
        f"be metadata, since everything below one is metadata too"
    )


@template("mount-duplicate")
def _mount_duplicate(name: Namer, /, *, mount: str, **_: Any) -> str:
    return f"more than one store is mounted at {keys.displayed(mount)!r}"


@template("mount-read-only-unmatched")
def _mount_read_only_unmatched(name: Namer, /, *, mounts: object, **_: Any) -> str:
    listed = ", ".join(repr(keys.displayed(m)) for m in mounts)  # type: ignore[union-attr]
    return f"nothing is mounted at {listed}, so it cannot be mounted read-only"


@template("mount-table-has-no-root")
def _mount_table_has_no_root(name: Namer, /, **_: Any) -> str:
    return (
        "a mount table needs a store at the root, since it is what owns "
        "every key no other mount claims"
    )


@template("mount-spec-malformed")
def _mount_spec_malformed(name: Namer, /, *, spec: str, delimiter: str = "=", **_: Any) -> str:
    return f"mount {spec!r} is not in KEY{delimiter}FILE form, as in ref{delimiter}reference.sqlite"


@template("mount-spec-has-no-file")
def _mount_spec_has_no_file(name: Namer, /, *, spec: str, **_: Any) -> str:
    return f"mount {spec!r} names no store file"


@template("mount-option-malformed")
def _mount_option_malformed(
    name: Namer, /, *, spec: str, option: str, assignment: str = "=", **_: Any
) -> str:
    return (
        f"{option!r} in mount {spec!r} is not an option: an option after the "
        f"store file is written NAME{assignment}VALUE, as in type{assignment}files"
    )


@template("mount-option-unknown")
def _mount_option_unknown(name: Namer, /, *, spec: str, option: str, known: Any, **_: Any) -> str:
    listed = ", ".join(str(one) for one in known)
    return (
        f"mount {spec!r} sets {option!r}, which is not a mount option. "
        f"There is: {listed}. A comma in the argument starts an option, so a "
        f"store file cannot hold one."
    )


@template("mount-option-repeated")
def _mount_option_repeated(name: Namer, /, *, spec: str, option: str, **_: Any) -> str:
    return f"mount {spec!r} sets {option!r} twice, and only one of them can be meant"


@template("mount-file-unspellable")
def _mount_file_unspellable(name: Namer, /, *, file: str, delimiter: str = ",", **_: Any) -> str:
    return (
        f"the store file {file!r} cannot be named on a command line: a "
        f"{delimiter!r} in a mount argument starts an option, so a store file "
        f"holding one has no spelling that reads back as itself"
    )


@template("mount-spec-at-root")
def _mount_spec_at_root(name: Namer, /, *, spec: str, **_: Any) -> str:
    return f"mount {spec!r} has no mount point; the store at the root is the one --root-mount names"


@template("mount-read-only-missing")
def _mount_read_only_missing(name: Namer, /, *, mount: str, path: str, **_: Any) -> str:
    return (
        f"the read-only mount at {keys.displayed(mount)!r} has no store at "
        f"{path!r}. A read-only mount is not created, since a "
        f"mistyped name would mount as an empty store that no write could "
        f"ever contradict."
    )


@template("documents-not-installed")
def _documents_not_installed(name: Namer, /, *, path: str, **_: Any) -> str:
    return (
        f"the outrage documentation is not in this installation: nothing at "
        f"{path!r}. It ships inside the package, so a missing tree is a build "
        f"that dropped it rather than anything to configure."
    )


# A mount configuration file. Every one of these names the file, because a
# table read from disk is the one kind nobody was looking at when it broke:
# unlike an option, it was written some other day, possibly by somebody else,
# and quite possibly for a different checkout.


@template("mount-unmount-at-root")
def _mount_unmount_at_root(name: Namer, /, **_: Any) -> str:
    return (
        "the store at the root cannot be unmounted: it owns every key no "
        "mount claims, so nothing would answer for them. --root-mount is how "
        "a different store is put there."
    )


@template("mount-unmount-unmatched")
def _mount_unmount_unmatched(name: Namer, /, *, mount: str, **_: Any) -> str:
    return (
        f"nothing is mounted at {keys.displayed(mount)!r}, so --unmount there "
        f"removes nothing. Refused rather than passed over, since what a "
        f"mistyped one leaves behind is the mount it was meant to take away."
    )


@template("mount-config-missing")
def _mount_config_missing(name: Namer, /, *, path: str, **_: Any) -> str:
    return f"there is no mount configuration at {path!r}"


@template("mount-config-unreadable")
def _mount_config_unreadable(name: Namer, /, *, path: str, reason: str, **_: Any) -> str:
    return f"the mount configuration at {path!r} could not be read: {reason}"


@template("mount-config-not-toml")
def _mount_config_not_toml(name: Namer, /, *, path: str, reason: str, **_: Any) -> str:
    return f"the mount configuration at {path!r} is not valid TOML: {reason}"


@template("mount-config-unknown-field")
def _mount_config_unknown_field(
    name: Namer, /, *, path: str, fields: object, known: object, **_: Any
) -> str:
    named = ", ".join(repr(field) for field in fields)  # type: ignore[union-attr]
    expected = ", ".join(repr(field) for field in known)  # type: ignore[union-attr]
    return (
        f"the mount configuration at {path!r} sets {named}, which means "
        f"nothing here; it holds {expected} and nothing else"
    )


@template("mount-config-not-a-table")
def _mount_config_not_a_table(
    name: Namer, /, *, path: str, field: str, got: str, **_: Any
) -> str:
    return (
        f"{field!r} in the mount configuration at {path!r} is a {got} rather "
        f"than a table of KEY = \"FILE\" entries"
    )


@template("mount-config-not-a-file")
def _mount_config_not_a_file(name: Namer, /, *, path: str, field: str, got: str, **_: Any) -> str:
    return (
        f"{field!r} in the mount configuration at {path!r} is a {got} rather "
        f"than the name of a store file"
    )


@template("mount-config-section-is-an-entry")
def _mount_config_section_is_an_entry(
    name: Namer, /, *, path: str, field: str, key: str, **_: Any
) -> str:
    return (
        f"[{field}] in the mount configuration at {path!r} is one entry's "
        f"fields rather than a table of mounts: {key!r} belongs inside an "
        f"entry, as in docs = {{ {key} = \"documents\", type = \"files\" }}"
    )


@template("mount-config-unknown-option")
def _mount_config_unknown_option(
    name: Namer, /, *, path: str, field: str, options: object, known: object, **_: Any
) -> str:
    named = ", ".join(repr(option) for option in options)  # type: ignore[union-attr]
    expected = ", ".join(repr(option) for option in known)  # type: ignore[union-attr]
    return (
        f"{field!r} in the mount configuration at {path!r} sets {named}, which "
        f"is not something a mount can say; an entry holds {expected}"
    )


@template("mount-config-no-path")
def _mount_config_no_path(name: Namer, /, *, path: str, field: str, key: str, **_: Any) -> str:
    return (
        f"{field!r} in the mount configuration at {path!r} names no store "
        f"file: an entry written as a table needs {key!r}"
    )


@template("mount-config-duplicate")
def _mount_config_duplicate(name: Namer, /, *, path: str, mount: str, **_: Any) -> str:
    return (
        f"the mount configuration at {path!r} mounts {keys.displayed(mount)!r} "
        f"twice; read-write and read-only mounts share one namespace"
    )


@template("mount-config-unspellable")
def _mount_config_unspellable(
    name: Namer, /, *, path: str, mount: str, delimiter: str, **_: Any
) -> str:
    return (
        f"{mount!r} in the mount configuration at {path!r} cannot be a mount "
        f"point: it holds {delimiter!r}, so it has no --mount spelling, and a "
        f"configuration file is read as the options it stands for"
    )


@template("cursor-outside-subtree")
def _cursor_outside_subtree(name: Namer, /, *, cursor: str, mount: str, key: str, **_: Any) -> str:
    return (
        f"cursor {cursor!r} is not below {keys.displayed(mount)!r}, which is the "
        f"store answering for {keys.displayed(key)!r}"
    )


# -- maintenance, the log, configuration -----------------------------------


@template("check-unreadable")
def _check_unreadable(name: Namer, /, *, path: str, reason: str, **_: Any) -> str:
    return f"cannot read {path}: {reason}"


@template("check-no-store")
def _check_no_store(name: Namer, /, *, path: str, **_: Any) -> str:
    return f"no store at {path}"


@template("log-missing")
def _log_missing(name: Namer, /, *, path: str, **_: Any) -> str:
    return f"no log file at {path}"


@template("log-unreadable")
def _log_unreadable(name: Namer, /, *, path: str, reason: str, **_: Any) -> str:
    return f"cannot read {path}: {reason}"


@template("config-not-json")
def _config_not_json(name: Namer, /, *, path: str, reason: str, **_: Any) -> str:
    return f"{path} is not valid JSON ({reason}); leaving it alone"


@template("config-not-an-object")
def _config_not_an_object(name: Namer, /, *, path: str, **_: Any) -> str:
    return f"{path} does not hold a JSON object; leaving it alone"


@template("config-field-not-an-object")
def _config_field_not_an_object(name: Namer, /, *, path: str, field: str, **_: Any) -> str:
    return f"{path} has a {field!r} that is not an object; leaving it alone"


@template("config-field-not-a-list")
def _config_field_not_a_list(name: Namer, /, *, path: str, field: str, **_: Any) -> str:
    return f"{path} has a {field!r} that is not a list; leaving it alone"


@template("config-server-not-an-object")
def _config_server_not_an_object(name: Namer, /, *, path: str, server: str, **_: Any) -> str:
    return f"{path} has a {server!r} server that is not an object; leaving it alone"


# -- installation ----------------------------------------------------------


@template("template-missing")
def _template_missing(name: Namer, /, *, path: str, **_: Any) -> str:
    return f"packaged template missing at {path}"


@template("template-not-json")
def _template_not_json(name: Namer, /, *, path: str, **_: Any) -> str:
    return f"packaged template at {path} is not valid JSON"


@template("template-hook-count")
def _template_hook_count(name: Namer, /, *, event: str, **_: Any) -> str:
    return f"packaged template must hold exactly one {event} entry"


@template("template-unmarked")
def _template_unmarked(name: Namer, /, *, marker: str, **_: Any) -> str:
    return f"packaged template's command does not carry the {marker!r} marker"


@template("assets-missing")
def _assets_missing(name: Namer, /, *, asset: str, path: str, **_: Any) -> str:
    return f"packaged {asset} missing at {path}"


@template("assets-empty")
def _assets_empty(name: Namer, /, *, asset: str, path: str, **_: Any) -> str:
    return f"packaged {asset} content is empty at {path}"


# -- store: which backend, and what it will not do -------------------------


@template("store-read-only")
def _store_read_only(name: Namer, /, *, key: str, path: str, action: str, **_: Any) -> str:
    # Deliberately does *not* offer a flag to drop, which is what separates
    # this from `mount-read-only`: no way of opening a parquet file makes a
    # write to it succeed, and advice that cannot work is worse than none. It
    # reaches a caller through a mount as well as through a bare store --
    # `Resolved.writable` picks between the two refusals by asking the store
    # rather than the configuration.
    return (
        f"cannot {action} {name(key)!r}: it is in a parquet store, which is "
        f"written whole rather than updated in place. No way of starting the "
        f"server allows a write here; build a new one with `outrage pack`. "
        f"({path})"
    )


@template("backend-unavailable")
def _backend_unavailable(
    name: Namer, /, *, filename: str, backend: str, reason: str, **_: Any
) -> str:
    return f"{filename} needs the {backend} backend, which will not load: {reason}"


@template("backend-unknown")
def _backend_unknown(name: Namer, /, *, backend: str, filename: str, known: Any, **_: Any) -> str:
    listed = ", ".join(str(one) for one in known)
    about = f" for {filename!r}" if filename else ""
    return (
        f"there is no {backend!r} backend{about}. The types a mount may ask "
        f"for are: {listed}. Asked for rather than guessed at, so a name "
        f"nobody recognises is refused instead of quietly opening an empty "
        f"store of some other kind."
    )


@template("parquet-needs-pyarrow")
def _parquet_needs_pyarrow(name: Namer, /, *, reason: str, **_: Any) -> str:
    return (
        f"a parquet store needs pyarrow, which is not installed: {reason}. "
        f"Install it with `pip install 'outrage[parquet]'`."
    )


@template("parquet-store-missing")
def _parquet_store_missing(name: Namer, /, *, path: str, **_: Any) -> str:
    return (
        f"there is no parquet store at {path}. Unlike a SQLite store this one "
        f"is not created empty: it has no write that would fill it, so an "
        f"empty one could only ever read back empty. Build it with `outrage pack`."
    )


@template("parquet-not-a-store")
def _parquet_not_a_store(name: Namer, /, *, path: str, **_: Any) -> str:
    return (
        f"{path} is a parquet file but not an outrage store: it carries no format "
        f"version, so its columns are somebody else's and mean something else"
    )


@template("parquet-format-newer")
def _parquet_format_newer(name: Namer, /, *, path: str, found: int, expected: int, **_: Any) -> str:
    return (
        f"{path} is written in parquet store format {found} and this build "
        f"reads {expected}; it is not migrated in place, so repack it or "
        f"upgrade outrage"
    )


@template("parquet-target-exists")
def _parquet_target_exists(name: Namer, /, *, path: str, **_: Any) -> str:
    return f"{path} already exists; pass --overwrite to replace it"


@template("parquet-build-wildcard")
def _parquet_build_wildcard(name: Namer, /, *, key: str, **_: Any) -> str:
    return (
        f"cannot pack {key!r}: a '?' is allocated by reading the store for a "
        f"free number, and a store being built has nothing to read"
    )


# -- the command line ------------------------------------------------------


@template("content-two-sources")
def _content_two_sources(name: Namer, /, **_: Any) -> str:
    return "give --content or --file, not both"


@template("content-unreadable")
def _content_unreadable(name: Namer, /, *, path: str, reason: str, **_: Any) -> str:
    return f"cannot read {path}: {reason}"


@template("content-missing")
def _content_missing(name: Namer, /, **_: Any) -> str:
    return "nothing to store: pass --content, --file, or pipe it in"


@template("copy-target-inside-source")
def _copy_target_inside_source(
    name: Namer, /, *, source: str, target: str, **_: Any
) -> str:
    return (
        f"cannot copy {name(source)!r} beneath {name(target)!r}: the target is "
        "inside the source subtree, and a streaming copy would read what it just wrote"
    )


@template("copy-source-inside-target")
def _copy_source_inside_target(
    name: Namer, /, *, source: str, target: str, **_: Any
) -> str:
    return (
        f"cannot re-root {name(source)!r} onto {name(target)!r}: the source is "
        "inside the target subtree, so a re-rooted copy would write back into "
        "what it is still reading. Copy it to a key outside the target first"
    )


__all__ = ["Namer", "codes", "render", "template"]
