"""Write a `!title` beside every markdown document in a tree, from its heading.

A directory of files mounted `type=files` is a store like any other, and this
store is navigated by `get_documents(meta_name=["title"])` -- so a page with no
`!title` is invisible to a survey and shows up only in `without_meta`. Generated
pages arrive without one. This fills them in.

The mapping is `outrage.bulk`'s, unchanged: a document `a/b` is the file
`a/b.md`, and its metadata `a/b/!title` is the file `a/b/!title.md`. So the
title for `reference/store.md` goes in `reference/store/!title.md`, whether or
not that directory already exists -- which is the same rule for a page with
children and a page without.

A title is matched by its *key*, not by its filename: a hand-written
`!title.txt` is the same key as a generated `!title.md` and is left alone
rather than written beside. See `title_file`.

**Existing titles are left alone.** Every hand-written document in
`src/outrage/documents` has a title that is deliberately not its heading:
`keys.md` leads with "What a key is" and is titled "Keys: the grammar of the
namespace". A run over the whole tree would flatten all five back to their
headings, so the default is to skip what is already there and `--overwrite` is
the way to ask for the other thing.

The heading is the first ATX `#` line. A heading is a weaker title than the
module docstring's first sentence -- it names the page rather than saying what
is in it -- and the docstring is the alternative if these ever read too thin.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from outrage.titles import markdown_title

#: The metadata segment this writes. A leading `!` opens a metadata namespace on
#: the key above it, which is what makes this a title rather than a document
#: called "!title".
TITLE_KEY = "!title"

#: The extension used when writing a title that is not there yet. An existing
#: one keeps whatever extension it has -- see `title_file`.
TITLE_FORMAT = ".md"


def title_file(directory: Path) -> Path:
    """Where `directory`'s title goes: the file already claiming that key, or a new one.

    **The extension is not part of the key.** `!title.md` and `!title.txt` are
    both the key `!title`, differing only in the format they name, so a tree
    holding both holds one key twice -- which `FilesystemStore.check_file`
    reports as "keys held by more than one file", resolving it silently to the
    first in name order. Matching on `!title.md` alone is how this function got
    written the first time, and it wrote a second file beside a hand-written
    `!title.txt` rather than leaving it alone.
    """
    claimed = sorted(directory.glob(f"{TITLE_KEY}.*")) if directory.is_dir() else []
    return claimed[0] if claimed else directory / (TITLE_KEY + TITLE_FORMAT)


def documents(tree: Path):
    """Every markdown document in `tree`, metadata files excluded.

    A file whose name begins with `!` is metadata, not a document, and giving
    a title a title of its own is not what anybody means by this.
    """
    for path in sorted(tree.rglob("*.md")):
        if not path.name.startswith("!"):
            yield path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tree", type=Path, help="directory of markdown documents")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace titles that are already there, rather than skipping them",
    )
    parser.add_argument("-n", "--dry-run", action="store_true", help="report without writing")
    args = parser.parse_args(argv)

    if not args.tree.is_dir():
        print(f"not a directory: {args.tree}", file=sys.stderr)
        return 1

    written = skipped = untitled = 0
    for path in documents(args.tree):
        title = markdown_title(path.read_text())
        if title is None:
            print(f"  no heading: {path.relative_to(args.tree)}", file=sys.stderr)
            untitled += 1
            continue
        target = title_file(path.with_suffix(""))
        if target.exists() and not args.overwrite:
            skipped += 1
            continue
        if not args.dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(title + "\n")
        written += 1
        print(f"  {path.relative_to(args.tree).with_suffix('')}: {title}")

    verb = "would write" if args.dry_run else "wrote"
    print(f"{verb} {written}, skipped {skipped} already titled, {untitled} without a heading")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
