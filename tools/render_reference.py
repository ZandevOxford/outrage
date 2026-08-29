"""Rearrange the markdown Sphinx builds into the section the store mounts.

`make markdown` in `docs/` writes what the HTML build writes: a landing page at
`index.md` and the module pages under `api/`. Mounted as it stands that is
`outrage/reference/api/<module>`, and `ls outrage/reference` answers with one
implicit key called `api` -- a listing of the section that tells a reader
nothing. This flattens it to `outrage/reference/<module>`.

Three moves, and each is a decision recorded in `context/71` in the outrage
store rather than a tidy-up:

* **Sphinx's `index.md` is dropped.** It restates the shipped `readme`, and it
  is the only page carrying links to `genindex`, `py-modindex` and `search`,
  which the markdown builder does not generate. Dropping it removes all three
  dead links.
* **`api/index.md` becomes `reference.md`**, beside the directory rather than
  inside it: in this mapping the document *at* `outrage/reference` is the file
  next to the directory. That page is the grouped reading order -- namespace,
  storage, front ends, around the edges -- and it reads as a section index with
  nothing rewritten but its links.
* **The module pages move up.** They travel together, so their links to each
  other are unchanged; only the promoted page moved relative to them, so only
  its links are rewritten.

Titles are not written here. `tools/document_titles.py` does that, over the
whole tree, so that the one rule about not overwriting a hand-written title
lives in one place.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

#: The key the section is mounted at, and so the name of both the directory and
#: the file beside it. `outrage/reference` as a key; `reference.md` and
#: `reference/` on disk.
SECTION = "reference"

#: Where the module pages sit in the Sphinx output, from `docs/api/`.
SOURCE_SUBDIR = "api"

#: A relative link to a sibling module page, as the promoted landing page holds
#: it -- `](keys.md)` or `](store.md#module-outrage.store)`. Anchored on `](`
#: so it cannot match prose, and excluding a scheme so the absolute links to
#: docs.python.org are left alone.
SIBLING_LINK = re.compile(r"\]\((?!\w+:)([a-z_]+)\.md")


def rearrange(build: Path, dest: Path) -> int:
    """Write `dest/reference.md` and `dest/reference/` from a markdown build.

    Whatever was at either path is removed first: this is generated output, and
    a stale page left behind by a rename would otherwise still mount, still
    read, and still look exactly as correct as the rest.
    """
    pages = sorted((build / SOURCE_SUBDIR).glob("*.md"))
    if not pages:
        print(f"no pages in {build / SOURCE_SUBDIR}", file=sys.stderr)
        return 1
    landing = build / SOURCE_SUBDIR / "index.md"
    if not landing.is_file():
        print(f"no landing page at {landing}", file=sys.stderr)
        return 1

    section_dir, section_file = dest / SECTION, dest / f"{SECTION}.md"
    for stale in (section_dir, section_file):
        if stale.is_dir():
            shutil.rmtree(stale)
        elif stale.exists():
            stale.unlink()
    section_dir.mkdir(parents=True)

    section_file.write_text(SIBLING_LINK.sub(rf"]({SECTION}/\1.md", landing.read_text()))
    written = 0
    for page in pages:
        if page != landing:
            shutil.copy(page, section_dir / page.name)
            written += 1
    print(f"{SECTION}.md from {landing.name}, {written} pages in {SECTION}/")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("build", type=Path, help="the markdown build, e.g. docs/_build/markdown")
    parser.add_argument("dest", type=Path, help="the documents tree to write the section into")
    args = parser.parse_args(argv)

    if not args.build.is_dir():
        print(f"not a directory: {args.build}", file=sys.stderr)
        return 1
    if not args.dest.is_dir():
        print(f"not a directory: {args.dest}", file=sys.stderr)
        return 1
    return rearrange(args.build, args.dest)


if __name__ == "__main__":
    raise SystemExit(main())
