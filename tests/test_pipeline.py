"""Stage handoffs, resumable discovery, and preservation of missing sources."""

import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from anekanta.acquire import acquire
from anekanta.contracts import load_manifest
from anekanta.discover import discover
from anekanta.review import run as import_review

ROOT = Path(__file__).resolve().parents[1]
OPENALEX = "https://openalex.org"
SNAPSHOT = ROOT / "tests/fixtures/openalex-hayes-lawless.json"
PILOT = ROOT / "testdata/iyengar-2012.json"
ANNOTATION = ROOT / "schema/examples/hayes-lawless.json"


def test_discovery_checkpoint_retry_and_deduplication(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
    args = SimpleNamespace(
        doi="10.1093/poq/nfs038",
        citing_doi=None,
        max_pages=1,
        output=tmp_path / "discovery.json",
        resume=False,
    )
    cursors = []
    works = [
        {"id": f"{OPENALEX}/W2", "doi": "https://doi.org/10.1017/s1537592714003156"},
        {"id": f"{OPENALEX}/W3", "doi": "https://doi.org/10.1017/s1537592714003156"},
        {"id": f"{OPENALEX}/W4", "doi": None},
    ]

    def handle(request):
        assert request.url.params["api_key"] == "test-key"
        if request.url.path != "/works":
            return httpx.Response(
                200,
                json={
                    "id": f"{OPENALEX}/W1",
                    "doi": args.doi,
                    "display_name": "Target",
                },
            )
        assert request.url.params["filter"] == "cites:W1"
        cursor = request.url.params["cursor"]
        cursors.append(cursor)
        if cursors == ["*", "second"]:
            return httpx.Response(429)
        page = works[:1] if cursor == "*" else works[1:]
        return httpx.Response(
            200,
            json={
                "meta": {
                    "count": 3,
                    "next_cursor": "second" if cursor == "*" else None,
                },
                "results": page,
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        discover(args, client)
        first = args.output.read_bytes()
        assert not json.loads(first)["complete"]
        args.resume = True
        with pytest.raises(ValueError, match="429"):
            discover(args, client)
        assert args.output.read_bytes() == first
        discover(args, client)
        discover(args, client)
    result = json.loads(args.output.read_text())
    assert cursors == ["*", "second", "second"]
    assert result["complete"]
    assert result["reported_count"] == 3
    assert [p["citing_work"]["id"] for p in result["papers"]] == [
        "doi:10.1017/s1537592714003156",
        "openalex:W4",
    ]
    assert result["papers"][0]["openalex_ids"] == ["W2", "W3"]
    assert "test-key" not in args.output.read_text()


def test_local_acquisition_and_review(tmp_path, capsys):
    manifest = tmp_path / "manifest.json"
    args = SimpleNamespace(
        discovery=SNAPSHOT,
        output=manifest,
        offline=True,
        local_manifest=None,
        allow_partial=False,
    )
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: pytest.fail("offline"))
    ) as client:
        acquire(args, client)
        missing = load_manifest(manifest)
        assert len(missing["papers"]) == 1
        assert "unavailable" in missing["papers"][0]
        args.local_manifest = PILOT
        acquire(args, client)
    inventory = load_manifest(manifest)
    assert inventory["discovery"]["complete"]
    assert len(inventory["papers"]) == 1
    paper = inventory["papers"][0]
    pdf = manifest.parent / paper["path"]
    assert pdf.read_bytes() == (PILOT.parent / "13.pdf").read_bytes()
    review = SimpleNamespace(manifest=manifest, record=ANNOTATION)
    assert import_review(review) == 0
    row = json.loads(capsys.readouterr().out)
    assert row["method"]["name"] == "manual"
    assert row["source"]["location"] == paper["path"]
    assert row["passages"][0]["location"]["pdf_page"] == 4
    assert row["passages"][0]["note"]["location"]["pdf_page"] == 16
    pdf.write_bytes((PILOT.parent / "4.pdf").read_bytes())
    with pytest.raises(ValueError, match="different PDF"):
        import_review(review)


def test_acquisition_falls_back_and_keeps_failed_works(tmp_path):
    state = json.loads(SNAPSHOT.read_text())
    paper = state["papers"][0]
    paper["pdf_urls"] = ["https://example.org/html", "https://example.org/pdf"]
    state["papers"].append(
        {
            "citing_work": {"id": "openalex:W123"},
            "openalex_ids": ["W123"],
            "pdf_urls": ["https://example.org/missing"],
        }
    )
    state.update(complete=False, next_cursor="more")
    discovery = tmp_path / "discovery.json"
    discovery.write_text(json.dumps(state))
    args = SimpleNamespace(
        discovery=discovery,
        output=tmp_path / "manifest.json",
        offline=False,
        local_manifest=None,
        allow_partial=False,
    )

    def handle(request):
        assert "api_key" not in request.url.params
        if request.url.path == "/pdf":
            return httpx.Response(200, content=(PILOT.parent / "13.pdf").read_bytes())
        return httpx.Response(
            404 if request.url.path == "/missing" else 200, text="<html>"
        )

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ValueError, match="incomplete"):
            acquire(args, client)
        args.allow_partial = True
        acquire(args, client)
    manifest = load_manifest(args.output)
    assert not manifest["discovery"]["complete"]
    found, missing = manifest["papers"]
    assert found["obtained_from"] == paper["pdf_urls"][1]
    assert "404" in missing["unavailable"]
