"""Acquire a source or record a reason for every discovered citing work."""

import hashlib
import json
from io import BytesIO
from pathlib import Path

import httpx
from pdfminer.pdfpage import PDFPage
from pdfminer.psexceptions import PSException

from anekanta.contracts import load_manifest, validate, validate_manifest
from anekanta.storage import save_bytes, save_json


def _pdf(data):
    if (
        b"%PDF-" not in data[:1024]
        or next(PDFPage.get_pages(BytesIO(data)), None) is None
    ):
        raise ValueError("Response contains no readable PDF page")
    return hashlib.sha256(data).hexdigest()


def _obtain(paper, catalog, args, client):
    work = paper["citing_work"]
    result = {"citing_work": work}
    local = catalog.get(work["id"])
    reasons = []
    sources = [(url, None) for url in paper["pdf_urls"]] if not args.offline else []
    if local and "path" in local:
        sources.insert(0, (str(args.local_manifest.parent / local["path"]), local))
    for source, entry in sources:
        try:
            if entry is None:
                if httpx.URL(source).scheme not in ("https", "http"):
                    raise ValueError("Unsupported PDF URL scheme")
                response = client.get(source)
                response.raise_for_status()
                data = response.content
            else:
                data = Path(source).read_bytes()
            digest = _pdf(data)
            if entry and entry["sha256"] != digest:
                raise ValueError("Local PDF does not match its catalog hash")
        except (OSError, ValueError, PSException, httpx.HTTPError) as error:
            reasons.append(f"{source}: {error}")
            continue
        rel = Path(args.output.stem + "-pdfs") / (digest + ".pdf")
        save_bytes(args.output.parent / rel, data)
        return {
            **result,
            "path": rel.as_posix(),
            "sha256": digest,
            "obtained_from": "local catalog" if entry else source,
        }
    detail = "No local match (offline)" if args.offline else "No open-access PDF URL"
    return {**result, "unavailable": " | ".join(reasons) or detail}


def acquire(args, client):
    """Write a complete manifest, retaining a reference to the discovery snapshot."""
    if args.output.resolve() in {
        args.discovery.resolve(),
        args.local_manifest.resolve() if args.local_manifest else None,
    }:
        raise ValueError("Output would overwrite a pipeline input")
    snapshot = args.discovery.read_bytes()
    state = json.loads(snapshot)
    validate("discovery.schema.json", state)
    if not state["complete"] and not args.allow_partial:
        raise ValueError("Discovery is incomplete. Resume it or pass --allow-partial.")
    catalog = {}
    if args.local_manifest:
        local = load_manifest(args.local_manifest)
        catalog = {p["citing_work"]["id"]: p for p in local["papers"]}
    out = {
        "cited_work": state["cited_work"],
        "discovery": {
            "provider": state["provider"],
            "started_at": state["started_at"],
            "complete": state["complete"],
            "citing_doi": state["citing_doi"],
            "reported_count": state["reported_count"],
            "sha256": hashlib.sha256(snapshot).hexdigest(),
        },
        "papers": [_obtain(paper, catalog, args, client) for paper in state["papers"]],
    }
    owners = {}
    for paper in out["papers"]:
        if "sha256" in paper:
            owners.setdefault(paper["sha256"], []).append(paper)
    for papers in owners.values():
        if len(papers) > 1:
            for paper in papers:
                for field in ("sha256", "path", "obtained_from"):
                    del paper[field]
                paper["unavailable"] = (
                    "The same PDF was supplied for distinct citing works"
                )
    validate_manifest(out)
    save_json(args.output, out)


def run(args):
    """Run acquisition using a client without OpenAlex credentials."""
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        acquire(args, client)
    return 0
