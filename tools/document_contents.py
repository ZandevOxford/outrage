"""Write a `!contents` offset index beside every markdown document in a tree.

`outrage.contents.make_contents` indexes one document. This walks a directory
of documents and indexes all of them, which is what the shipped tree needs: an
index is build output, like the reference pages it sits beside, so it belongs
in the documentation build rather than in whatever anybody remembers to run.

**Why the shipped documents want one at all.** They are the largest static text
this project ships and the least likely to be read whole -- `reference/store`
is 96k characters, `cli` 52k, `design` 55k. A generated reference page's
headings are its public names, so an index of one is a symbol table with two
offsets beside every entry, and a byte-addressed read jumps straight to a class
or a function. An index is the alternative to splitting such a document, not a
consolation for having failed to split it: one read of the index and one read
of the section costs what surveying titles and reading a child would.

**It goes through the store rather than over the files.** Every question about
where an index lands is one :class:`outrage.store_files.FilesystemStore`
already answers: `x/!contents` is the file `x/!contents.md` beside `x.md`, and
a key already claimed by a file with another extension keeps that file. Writing
the files directly means restating that mapping, and `tools/document_titles.py`
carries the scar -- it wrote `!title.md` beside a hand-written `!title.txt`,
two files for one key, resolved silently by name order.

**A stale index is worse than none**, because its offsets point into a document
that has moved and nothing about reading one says it is out of date. So this
writes what changed rather than skipping what is there -- the opposite of
`document_titles.py`, whose titles are deliberately not their headings and must
survive a run -- and `test_shipped.py` fails when the committed tree is not
what a run here would write.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from outrage import bulk, contents, keys, store
from outrage.store_files import FilesystemStore

#: The metadata name written, without its `!`. The default `make_contents`
#: takes, named here because the sweep and the guard in `tests/test_shipped.py`
#: have to agree on it.
CONTENTS_NAME = "contents"


@dataclass(frozen=True, slots=True)
class Swept:
    """What one sweep found, by key rather than by count.

    Keys rather than totals because both callers want them: the command line
    prints a line per document, and the currency guard fails naming the
    documents whose index has gone stale. A count would report that something
    is wrong and leave finding it to whoever reads the failure.
    """

    written: list[str] = field(default_factory=list)
    """Documents whose index was not what this run would write."""

    unchanged: list[str] = field(default_factory=list)
    """Documents already carrying the index this run would write."""

    headless: list[str] = field(default_factory=list)
    """Documents with no headings, which get no index at all."""

    removed: list[str] = field(default_factory=list)
    """Metadata keys taken away: an index whose document has lost its
    headings, which is the stale index this exists to prevent."""


def indexable(opened: store.Store):
    """Every markdown document in the store, in order.

    ``kind`` and ``format`` come off the listing, so nothing here parses a
    filename: a metadata key is skipped because the store says it is metadata,
    and a document is indexed because the store says it is markdown.
    :func:`outrage.contents.make_contents` refuses anything else, and refusing
    is right for one call and wrong for a sweep, which should pass over an HTML
    page rather than stop at it.

    A key that exists only because something is beneath it -- kind
    ``implicit`` -- has no document to index.
    """
    for entry in bulk.walk(opened, None):
        if entry.kind == "document" and entry.format == "markdown":
            yield entry.key


def stored_index(opened: store.Store, metadata_key: str) -> str | None:
    """What the store already holds at ``metadata_key``, or None for nothing.

    Read in full rather than sliced: this is compared against a whole
    rendering, and a capped read would report every index over the cap as
    changed and rewrite it on every run.
    """
    if not opened.exists(metadata_key):
        return None
    return store.read_all(opened, metadata_key).content


def sweep(
    opened: store.Store, *, metadata_name: str = CONTENTS_NAME, dry_run: bool = False
) -> Swept:
    """Bring every index in ``opened`` up to date with its document.

    With ``dry_run`` nothing is written and the result says what would have
    been. That is the mode the currency guard runs in, so the question the
    guard asks is exactly the question a run answers, rather than a second
    implementation of it.
    """
    swept = Swept()
    for key in list(indexable(opened)):
        metadata_key = f"{key}{keys.DELIMITER}{keys.META_PREFIX}{metadata_name}"
        rendered = contents.render_contents(store.read_all(opened, key).content)
        existing = stored_index(opened, metadata_key)

        if not rendered:
            # No headings, so there is nothing an index could address. The tool
            # pages under `tools/` are the ordinary case: a tool description is
            # prose, and one heading in fourteen of them would be a heading
            # nobody wrote.
            swept.headless.append(key)
            if existing is not None:
                # An index left behind by a document that has since lost its
                # headings is exactly the stale one this is here to prevent,
                # so it goes rather than being reported and left.
                if not dry_run:
                    opened.delete(metadata_key)
                swept.removed.append(metadata_key)
        elif existing == rendered:
            swept.unchanged.append(key)
        else:
            if not dry_run:
                contents.make_contents(opened, key, metadata_name=metadata_name)
            swept.written.append(key)
    return swept


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tree", type=Path, help="directory of markdown documents")
    parser.add_argument(
        "--metadata-name",
        default=CONTENTS_NAME,
        help=f"metadata to write, without its leading '!' (default: {CONTENTS_NAME})",
    )
    parser.add_argument("-n", "--dry-run", action="store_true", help="report without writing")
    args = parser.parse_args(argv)

    if not args.tree.is_dir():
        print(f"not a directory: {args.tree}", file=sys.stderr)
        return 1

    # Checked here rather than left to `make_contents`, which validates the
    # same thing on the way in: a dry run never reaches it, and a name the real
    # run would refuse should not preview as an index for every document.
    name = args.metadata_name
    if not name or name.startswith(keys.META_PREFIX) or keys.DELIMITER in name:
        print(f"not a direct metadata name: {name!r}", file=sys.stderr)
        return 1

    with FilesystemStore(args.tree, create=False) as opened:
        swept = sweep(opened, metadata_name=name, dry_run=args.dry_run)

    for key in swept.written:
        print(f"  {key}")
    for metadata_key in swept.removed:
        print(f"  {metadata_key}: removed, its document has no headings")

    verb = "would write" if args.dry_run else "wrote"
    print(
        f"{verb} {len(swept.written)}, {len(swept.unchanged)} already current, "
        f"{len(swept.headless)} without headings"
        + (f", {len(swept.removed)} stale removed" if swept.removed else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
