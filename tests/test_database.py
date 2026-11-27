import json
import sqlite3
from contextlib import closing
from types import SimpleNamespace

import pytest

from anekanta.database import run
from anekanta.discover import _paper


def test_load_preserves_provenance_and_rolls_back_bad_collections(tmp_path):
    row = {
        "schema_version": "0.1",
        "cited_work": {"id": "local:original"},
        "citing_work": _paper(
            {
                "id": "https://openalex.org/W1",
                "publication_year": 2020,
                "authorships": [{"author": {"display_name": "Example Author"}}],
                "primary_location": {"source": {"display_name": "Example Journal"}},
            }
        )["citing_work"],
        "method": {"name": "baseline", "version": "1"},
        "source": {"kind": "pdf", "sha256": "a" * 64, "location": "one.pdf"},
        "outcome": "passages_found",
        "passages": [
            {
                "id": "p3",
                "quote": "A citation",
                "location": {"pdf_page": 3},
                "review": "unchecked",
            }
        ],
    }
    absent = dict(
        row,
        citing_work={"id": "local:absent"},
        outcome="source_unavailable",
        detail="missing",
        passages=[],
    )
    del absent["source"]
    args = SimpleNamespace(
        db=tmp_path / "db.sqlite",
        collection="pilot",
        results=tmp_path / "input.jsonl",
        source_root=tmp_path,
    )
    export = json.dumps(row) + "\n" + json.dumps(absent) + "\n"
    args.results.write_text(export)
    assert run(args) == run(args) == 0
    args.results.write_text(export + "invalid\n")
    with pytest.raises(ValueError, match="different inputs"):
        run(args)
    args.collection = "another"
    with pytest.raises(ValueError, match="line 3"):
        run(args)
    with closing(sqlite3.connect(args.db)) as db:
        assert db.execute("SELECT count(*) FROM results").fetchone() == (2,)
        assert db.execute("SELECT count(*) FROM collections").fetchone() == (1,)
        assert db.execute(
            "SELECT citing_id, pdf_page, quote FROM passages"
        ).fetchall() == [("openalex:W1", 3, "A citation")]
        metadata = db.execute(
            "SELECT metadata FROM work_metadata WHERE work_id = 'openalex:W1'"
        ).fetchone()[0]
        assert json.loads(metadata) == row["citing_work"]
