"""Store versioned citation-search results and their passages in SQLite."""

import hashlib
import json
import sqlite3
from contextlib import closing

from jsonschema import ValidationError

from anekanta.contracts import VALIDATOR

SCHEMA = """
BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS collections (
    collection TEXT PRIMARY KEY NOT NULL,
    export_sha256 TEXT NOT NULL,
    source_root TEXT,
    imported_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS results (
    collection TEXT NOT NULL REFERENCES collections DEFERRABLE INITIALLY DEFERRED,
    cited_id TEXT NOT NULL,
    citing_id TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    method TEXT NOT NULL,
    outcome TEXT NOT NULL,
    record TEXT NOT NULL,
    PRIMARY KEY (collection, cited_id, citing_id, source_sha256, method)
);
CREATE INDEX IF NOT EXISTS results_by_target ON results(cited_id);
CREATE INDEX IF NOT EXISTS results_by_citer ON results(citing_id);
CREATE VIEW IF NOT EXISTS passages AS
    SELECT collection, cited_id, citing_id, source_sha256, method,
           json_extract(p.value, '$.id') AS passage_id,
           json_extract(p.value, '$.quote') AS quote,
           json_extract(p.value, '$.location.pdf_page') AS pdf_page,
           json_extract(p.value, '$.review') AS review,
           json_extract(record, '$.source.location') AS source_location,
           p.value AS passage
    FROM results, json_each(record, '$.passages') AS p;
CREATE VIEW IF NOT EXISTS work_metadata AS
    SELECT DISTINCT collection, citing_id AS work_id,
           json_extract(record, '$.citing_work') AS metadata FROM results
    UNION
    SELECT DISTINCT collection, cited_id, json_extract(record, '$.cited_work')
    FROM results;
"""


def _insert(db, collection, line):
    record = json.loads(line)
    VALIDATOR.validate(record)
    ids = [p["id"] for p in record["passages"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate passage identifier within a result")
    db.execute(
        "INSERT INTO results VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            collection,
            record["cited_work"]["id"],
            record["citing_work"]["id"],
            record.get("source", {}).get("sha256", ""),
            json.dumps(record["method"], sort_keys=True),
            record["outcome"],
            json.dumps(record, ensure_ascii=False, sort_keys=True),
        ),
    )


def run(args):
    """Import one immutable, named collection of JSON Lines in one transaction."""
    if not args.collection.strip():
        raise ValueError("Specify a nonempty collection name")
    root = str(args.source_root.resolve()) if args.source_root else None
    digest = hashlib.sha256()
    with args.results.open("rb") as stream, closing(sqlite3.connect(args.db)) as db, db:
        db.execute("PRAGMA foreign_keys = ON")
        db.executescript(SCHEMA)
        previous = db.execute(
            "SELECT export_sha256, source_root FROM collections WHERE collection = ?",
            (args.collection,),
        ).fetchone()
        for number, line in enumerate(stream, start=1):
            digest.update(line)
            if previous is None:
                try:
                    _insert(db, args.collection, line)
                except (ValueError, ValidationError, sqlite3.IntegrityError) as error:
                    raise ValueError(
                        f"{args.results}, line {number}: {error}"
                    ) from error
        if previous is None:
            db.execute(
                "INSERT INTO collections (collection, export_sha256, source_root) "
                "VALUES (?, ?, ?)",
                (args.collection, digest.hexdigest(), root),
            )
        elif previous != (digest.hexdigest(), root):
            raise ValueError("Collection already exists with different inputs")
    return 0
