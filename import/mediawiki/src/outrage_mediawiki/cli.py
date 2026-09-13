"""The ``mediawiki-import`` command line."""

from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from pathlib import Path

from .convert import Conversion, convert_part
from .fetch import fetch_part, sha256_file
from .source import DEFAULT_SOURCE, Dump, Part, resolve


def parser() -> argparse.ArgumentParser:
    """Build the argument parser separately so its contract is testable."""
    out = argparse.ArgumentParser(
        prog="mediawiki-import",
        description=(
            "Import a Wikimedia content dump into a directory of Parquet parts. The newest "
            "completed mediawiki_content_current dump of one wiki is resolved, each compressed "
            "XML piece is downloaded and checked against the dump's SHA256SUMS, and each is "
            "converted into one Parquet part as soon as it is verified, while the next one "
            "downloads. The target directory opens as an Outrage DuckDB store, readable part "
            "by part as the parts complete. Downloads resume, and a verified download or a "
            "part whose conversion receipt matches is reused, so an interrupted run is "
            "finished by running it again."
        ),
    )
    out.add_argument(
        "--download-dir",
        required=True,
        type=Path,
        metavar="DIR",
        help="where downloads and conversion receipts are kept; the store goes inside it "
        "unless --target says otherwise",
    )
    out.add_argument(
        "--source-url",
        default=DEFAULT_SOURCE,
        metavar="URL",
        help="the dump index to resolve against (default: %(default)s)",
    )
    out.add_argument(
        "--wiki",
        default="enwiki",
        help="the wiki's database name, such as simplewiki (default: %(default)s)",
    )
    out.add_argument(
        "--month",
        help="the dump to use, as YYYY-MM for that month's newest or YYYY-MM-DD for one "
        "exact dump (default: the newest)",
    )
    out.add_argument(
        "--files",
        type=int,
        metavar="N",
        help="only the first N pieces in page-id order (default: every piece)",
    )
    out.add_argument(
        "--target",
        type=Path,
        metavar="DIR",
        help="the store directory the Parquet parts are written to (default: a directory "
        "named after --wiki inside --download-dir)",
    )
    out.add_argument(
        "--namespace",
        dest="namespaces",
        type=int,
        action="append",
        metavar="ID",
        help="a MediaWiki namespace number to import; repeat for several (default: 0, "
        "the articles)",
    )
    out.add_argument(
        "--redirects",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="store each redirect as an alias of the page it points at (default: on)",
    )
    out.add_argument(
        "--jobs",
        type=int,
        default=os.cpu_count() or 1,
        metavar="N",
        help="how many pieces to convert at once (default: the number of CPUs)",
    )
    out.add_argument(
        "--stage",
        choices=("resolve", "fetch", "convert", "all"),
        default="all",
        help="run only one step: resolve the dump, fetch its pieces, or convert pieces "
        "already downloaded (default: %(default)s)",
    )
    out.add_argument(
        "--dry-run",
        action="store_true",
        help="resolve the dump and list its pieces without downloading anything",
    )
    out.add_argument(
        "--overwrite",
        action="store_true",
        help="replace a Parquet part that has no matching conversion receipt rather than refusing",
    )
    return out


def _describe(dump: Dump, target: Path) -> None:
    total = sum(part.size for part in dump.parts)
    print(f"{dump.wiki} {dump.date}: {len(dump.parts)} part(s), {total} bytes")
    print(f"source: {dump.url}")
    print(f"target: {target} (duckdb directory)")
    for part in dump.parts:
        print(f"  {part.first_page:>9}-{part.last_page:<9} {part.size:>12}  {part.name}")


def _local(part: Part, download_dir: Path) -> Path:
    path = download_dir / part.name
    if not path.is_file():
        raise FileNotFoundError(f"downloaded part is missing: {path}")
    if path.stat().st_size != part.size or sha256_file(path) != part.sha256:
        raise ValueError(f"downloaded part does not match Wikimedia's checksum: {path}")
    return path


def _converted(result: tuple[Conversion, bool]) -> None:
    conversion, changed = result
    verb = "wrote" if changed else "reused"
    print(f"{verb} {conversion.target}: {conversion.rows} rows")


def _convert_many(
    inputs: list[tuple[Part, Path]],
    target: Path,
    receipts: Path,
    *,
    namespaces: frozenset[int],
    redirects: bool,
    overwrite: bool,
    jobs: int,
) -> None:
    workers = min(jobs, len(inputs))
    if workers <= 1:
        for part, path in inputs:
            _converted(
                convert_part(
                    part,
                    path,
                    target,
                    receipts,
                    namespaces=namespaces,
                    redirects=redirects,
                    overwrite=overwrite,
                )
            )
        return
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures: list[Future] = [
            executor.submit(
                convert_part,
                part,
                path,
                target,
                receipts,
                namespaces=namespaces,
                redirects=redirects,
                overwrite=overwrite,
            )
            for part, path in inputs
        ]
        for future in as_completed(futures):
            _converted(future.result())


def _fetch_and_convert(
    dump: Dump,
    download_dir: Path,
    target: Path,
    receipts: Path,
    *,
    namespaces: frozenset[int],
    redirects: bool,
    overwrite: bool,
    jobs: int,
) -> None:
    """Feed each verified download to conversion while the next one arrives."""
    workers = min(jobs, len(dump.parts))
    if workers <= 1:
        for part in dump.parts:
            path, changed = fetch_part(part, download_dir)
            print(f"{'downloaded' if changed else 'verified'} {path.name}")
            _converted(
                convert_part(
                    part,
                    path,
                    target,
                    receipts,
                    namespaces=namespaces,
                    redirects=redirects,
                    overwrite=overwrite,
                )
            )
        return
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures: list[Future] = []
        for part in dump.parts:
            path, changed = fetch_part(part, download_dir)
            print(f"{'downloaded' if changed else 'verified'} {path.name}")
            futures.append(
                executor.submit(
                    convert_part,
                    part,
                    path,
                    target,
                    receipts,
                    namespaces=namespaces,
                    redirects=redirects,
                    overwrite=overwrite,
                )
            )
        for future in as_completed(futures):
            _converted(future.result())


def run(arguments: argparse.Namespace) -> None:
    """Run a parsed command."""
    if arguments.jobs < 1:
        raise ValueError("--jobs must be at least 1")
    download_dir = arguments.download_dir.expanduser()
    target = (
        arguments.target.expanduser()
        if arguments.target is not None
        else download_dir / arguments.wiki
    )
    dump = resolve(
        source_url=arguments.source_url,
        wiki=arguments.wiki,
        month=arguments.month,
        files=arguments.files,
    )
    _describe(dump, target)
    if arguments.dry_run or arguments.stage == "resolve":
        return

    if arguments.stage == "fetch":
        for part in dump.parts:
            path, changed = fetch_part(part, download_dir)
            print(f"{'downloaded' if changed else 'verified'} {path.name}")
        return

    namespaces = frozenset(arguments.namespaces or [0])
    receipts = download_dir / ".mediawiki-import" / dump.wiki / dump.date
    if arguments.stage == "all":
        _fetch_and_convert(
            dump,
            download_dir,
            target,
            receipts,
            namespaces=namespaces,
            redirects=arguments.redirects,
            overwrite=arguments.overwrite,
            jobs=arguments.jobs,
        )
    else:
        inputs = [(part, _local(part, download_dir)) for part in dump.parts]
        _convert_many(
            inputs,
            target,
            receipts,
            namespaces=namespaces,
            redirects=arguments.redirects,
            overwrite=arguments.overwrite,
            jobs=arguments.jobs,
        )


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    try:
        arguments = parser().parse_args(argv)
        run(arguments)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"mediawiki-import: {exc}", file=sys.stderr)
        return 1
    return 0


__all__ = ["main", "parser", "run"]
