import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/quota-spending"


def test_quota_matrix_preserves_missing_and_unreadable_pairs():
    catalog = json.loads((EXAMPLE / "papers.json").read_text())
    sources = {p["work"]["id"]: p for p in catalog}
    targets = {key for key, paper in sources.items() if "search" in paper}
    # The column labels abbreviate the corresponding catalog entries.
    target_columns = {
        paper["label"].rsplit(" (", 1)[0]: target
        for target, paper in sources.items()
        if target in targets
    }
    rows = [
        json.loads(line)
        for line in (ROOT / "testout/quota-spending.jsonl").read_text().splitlines()
    ]
    results = {(r["citing_work"]["id"], r["cited_work"]["id"]): r for r in rows}
    assert len(rows) == len(results)
    assert set(results) == {(s, t) for s in sources for t in targets if s != t}

    with (EXAMPLE / "counts.csv").open(newline="") as stream:
        matrix = list(csv.DictReader(stream))
    assert len(matrix) == len(catalog)
    by_label = {p["label"]: key for key, p in sources.items()}
    assert {r["PDF searched"] for r in matrix} == set(by_label)
    for row in matrix:
        source = by_label[row.pop("PDF searched")]
        assert set(row) == set(target_columns)
        for column, cell in row.items():
            target = target_columns[column]
            if source == target:
                assert cell == ""
                continue
            record = results[source, target]
            assert record["source"]["sha256"] == sources[source]["sha256"]
            assert record["source"]["location"] == sources[source]["file"]
            if record["outcome"] == "extraction_failed":
                assert cell == "failed"
            else:
                assert int(cell) == len(record["passages"])
                assert record["outcome"] == (
                    "passages_found" if int(cell) else "no_match"
                )
