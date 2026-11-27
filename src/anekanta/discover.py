"""Enumerate incoming citations through the OpenAlex works API."""

import json
import os
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from anekanta.contracts import validate
from anekanta.storage import save_json

WORKS = "https://api.openalex.org/works"


def doi_id(value: str) -> str:
    """Normalize a DOI or DOI URL to the identifier used by Anekanta."""
    doi = value.strip().lower().removeprefix("https://doi.org/").removeprefix("doi:")
    if not doi.startswith("10.") or "/" not in doi or any(c.isspace() for c in doi):
        raise ValueError(f"Invalid DOI: {value!r}")
    return "doi:" + doi


def _get(client, url, params):
    key = os.environ.get("OPENALEX_API_KEY")
    if key:
        params = {**params, "api_key": key}
    response = client.get(url, params=params)
    if response.is_error:
        # The query string may contain an API key.
        msg = f"OpenAlex returned HTTP {response.status_code} for {url}"
        if response.status_code in (401, 403, 429):
            msg += ". Check OPENALEX_API_KEY and the API quota."
        raise ValueError(msg)
    return response.json()


def _paper(work):
    oa = work["id"].rsplit("/", 1)[-1]
    identifier = doi_id(work["doi"]) if work.get("doi") else "openalex:" + oa
    citing = {"id": identifier}
    if work.get("display_name"):
        citing["title"] = work["display_name"]
    urls = [
        location["pdf_url"]
        for location in work.get("locations", [])
        if location.get("is_oa") and location.get("pdf_url")
    ]
    return {
        "citing_work": citing,
        "openalex_ids": [oa],
        "pdf_urls": list(dict.fromkeys(urls)),
    }


def discover(args, client):
    """Save each completed page and resume from the recorded cursor."""
    target = doi_id(args.doi)
    subset = doi_id(args.citing_doi) if args.citing_doi else None
    if args.max_pages is not None and args.max_pages < 1:
        raise ValueError("--max-pages must be positive")
    if args.resume:
        state = json.loads(args.output.read_text(encoding="utf-8"))
        validate("discovery.schema.json", state)
        if state["cited_work"]["id"] != target or state["citing_doi"] != subset:
            raise ValueError("Output belongs to a different discovery query")
        if state["complete"]:
            return
    else:
        if args.output.exists():
            raise ValueError(
                "Discovery output exists. Use --resume or choose a new path."
            )
        url = WORKS + "/https://doi.org/" + quote(target[4:], safe="/")
        work = _get(client, url, {"select": "id,doi,display_name"})
        if doi_id(work["doi"]) != target:
            raise ValueError("OpenAlex resolved the query to another DOI")
        state = {
            "provider": "openalex",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "cited_work": {"id": target},
            "target_openalex_id": work["id"].rsplit("/", 1)[-1],
            "citing_doi": subset,
            "reported_count": None,
            "next_cursor": "*",
            "complete": False,
            "papers": [],
        }
        if work.get("display_name"):
            state["cited_work"]["title"] = work["display_name"]
        validate("discovery.schema.json", state)
        save_json(args.output, state)
    works = {row["citing_work"]["id"]: row for row in state["papers"]}
    filters = "cites:" + state["target_openalex_id"]
    if subset:
        filters += ",doi:" + subset[4:]
    seen = set()
    while not state["complete"]:
        cursor = state["next_cursor"]
        seen.add(cursor)
        page = _get(
            client,
            WORKS,
            {
                "filter": filters,
                "select": "id,doi,display_name,locations",
                "cursor": cursor,
                "per_page": 100,
            },
        )
        for work in page["results"]:
            row = _paper(work)
            previous = works.setdefault(row["citing_work"]["id"], row)
            for field in ("openalex_ids", "pdf_urls"):
                previous[field] = list(dict.fromkeys(previous[field] + row[field]))
        meta = page["meta"]
        next_cursor = meta.get("next_cursor") if page["results"] else None
        if next_cursor is not None and next_cursor in seen:
            raise ValueError("OpenAlex repeated a pagination cursor")
        state.update(
            reported_count=meta["count"],
            next_cursor=next_cursor,
            complete=next_cursor is None,
            papers=list(works.values()),
        )
        validate("discovery.schema.json", state)
        save_json(args.output, state)
        if len(seen) == args.max_pages:
            break


def run(args):
    """Run OpenAlex discovery using a network client."""
    with httpx.Client(timeout=30) as client:
        discover(args, client)
    return 0
