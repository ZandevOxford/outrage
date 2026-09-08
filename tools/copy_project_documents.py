"""Copy repository-level documents into the documentation shipped by Outrage."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

PROJECT_DOCUMENTS = {
    "README.md": "readme.md",
    "LICENSE": "license.md",
    "CHANGELOG.md": "changelog.md",
}


def copy_documents(repository: Path, destination: Path) -> list[Path]:
    """Copy the project documents from ``repository`` into ``destination``."""
    missing = [name for name in PROJECT_DOCUMENTS if not (repository / name).is_file()]
    if missing:
        raise FileNotFoundError(", ".join(str(repository / name) for name in missing))

    destination.mkdir(parents=True, exist_ok=True)
    written = []
    for source_name, destination_name in PROJECT_DOCUMENTS.items():
        target = destination / destination_name
        shutil.copyfile(repository / source_name, target)
        written.append(target)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="directory to receive the copied files")
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="repository root; defaults to the parent of tools",
    )
    args = parser.parse_args(argv)

    try:
        written = copy_documents(args.repository, args.destination)
    except FileNotFoundError as exc:
        print(f"missing project document: {exc}", file=sys.stderr)
        return 1
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
