"""Command-line entry point for the citation pipeline."""

import argparse
import sqlite3
from pathlib import Path

import httpx
from jsonschema import ValidationError

from anekanta import acquire, database, discover, extract, review


def main():
    """Run the requested stage and return its process exit status."""
    parser = argparse.ArgumentParser(prog="anekanta")
    stages = parser.add_subparsers(dest="stage", required=True)
    cmd = stages.add_parser("discover", help="enumerate citing works with OpenAlex")
    cmd.add_argument("doi")
    cmd.add_argument("--output", type=Path, required=True)
    cmd.add_argument("--resume", action="store_true")
    cmd.add_argument("--max-pages", type=int)
    cmd.add_argument(
        "--citing-doi", help="restrict discovery to a particular citing DOI"
    )
    cmd.set_defaults(run=discover.run)
    cmd = stages.add_parser("acquire", help="obtain a PDF or record its absence")
    cmd.add_argument("discovery", type=Path)
    cmd.add_argument("--output", type=Path, required=True)
    cmd.add_argument("--local-manifest", type=Path)
    cmd.add_argument("--offline", action="store_true")
    cmd.add_argument("--allow-partial", action="store_true")
    cmd.set_defaults(run=acquire.run)
    cmd = stages.add_parser("extract", help="locate author/year citation candidates")
    cmd.add_argument("manifest", type=Path)
    cmd.add_argument("--cache", type=Path)
    cmd.add_argument("--author", required=True)
    cmd.add_argument("--coauthor", help="second surname for a two-author citation")
    cmd.add_argument("--year", required=True)
    cmd.set_defaults(run=extract.run)
    cmd = stages.add_parser(
        "import-review", help="attach an existing checked annotation"
    )
    cmd.add_argument("manifest", type=Path)
    cmd.add_argument("record", type=Path)
    cmd.set_defaults(run=review.run)
    cmd = stages.add_parser("load", help="load citation results into a SQLite database")
    cmd.add_argument(
        "results", type=Path, help="JSON Lines from extract or import-review"
    )
    cmd.add_argument("--db", type=Path, required=True)
    cmd.add_argument("--collection", required=True, help="name for this export")
    cmd.add_argument(
        "--source-root", type=Path, help="base directory for PDF locations"
    )
    cmd.set_defaults(run=database.run)
    args = parser.parse_args()
    if args.stage == "extract" and (
        not args.author.strip()
        or (args.coauthor is not None and not args.coauthor.strip())
        or len(args.year) != 4
        or not args.year.isdecimal()
    ):
        parser.error("Specify a surname and four-digit publication year")
    try:
        return args.run(args)
    except (
        OSError,
        ValueError,
        ValidationError,
        httpx.RequestError,
        sqlite3.Error,
    ) as error:
        parser.exit(2, f"anekanta: {error}\n")
