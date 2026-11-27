"""Export unchecked author/year candidates from a manifest of local PDFs."""

import json
import re
import sys
from importlib.metadata import version

import ftfy

from anekanta.contracts import VALIDATOR, load_manifest
from anekanta.matching import author_year_pattern, split_sentences
from anekanta.pdf_text import cached_text, read_pdf


def find_passages(text, pattern):
    """Locate matches in normalized page text in reading order."""
    passages = []
    for page, raw in enumerate(text.split("\f"), start=1):
        normalized = " ".join(ftfy.fix_text(raw).split())
        offset = 0
        for sentence in split_sentences(normalized):
            passages.extend(
                {
                    "id": f"p{page}-char{offset + match.start()}",
                    "location": {"pdf_page": page},
                    "quote": sentence,
                    "review": "unchecked",
                }
                for match in pattern.finditer(sentence)
            )
            offset += len(sentence) + 1
    return passages


def extract(paper, root, manifest_dir, cited_work, method, pattern, cache):
    """Extract candidates after checking the source identity."""
    result = {
        "schema_version": "0.1",
        "cited_work": cited_work,
        "citing_work": paper["citing_work"],
        "method": method,
        "passages": [],
    }
    if "unavailable" in paper:
        return dict(result, outcome="source_unavailable", detail=paper["unavailable"])
    path = (manifest_dir / paper["path"]).resolve()
    try:
        data, digest = read_pdf(path)
    except OSError as error:
        return dict(result, outcome="source_unavailable", detail=str(error))
    if digest != paper["sha256"]:
        return dict(
            result,
            outcome="extraction_failed",
            detail=f"Expected {paper['sha256']} at {path}, read {digest}.",
        )
    location = path.relative_to(root) if path.is_relative_to(root) else path
    result["source"] = {
        "kind": "pdf",
        "location": str(location),
        "sha256": digest,
    }
    try:
        text = cached_text(data, digest, cache)
    except Exception as error:
        return dict(
            result,
            outcome="extraction_failed",
            detail=f"{type(error).__name__}: {error}",
        )
    if not text.strip():
        return dict(
            result,
            outcome="extraction_failed",
            detail="PDF has no readable text.",
        )
    result["passages"] = find_passages(text, pattern)
    result["outcome"] = "passages_found" if result["passages"] else "no_match"
    return result


def run(args):
    """Write a paper result for each inventory entry."""
    manifest = load_manifest(args.manifest)
    manifest_dir = args.manifest.resolve().parent
    root = (manifest_dir / manifest.get("source_root", ".")).resolve()
    search = {"author": args.author, "year": args.year}
    if args.coauthor:
        search["coauthor"] = args.coauthor
    pattern = re.compile(author_year_pattern(**search), re.IGNORECASE)
    pdfminer_version = version("pdfminer.six")
    method = {
        "name": "author-pair-year" if args.coauthor else "author-year",
        "version": f"1/pdfminer-{pdfminer_version}/ftfy-{version('ftfy')}",
        "parameters": search,
    }
    failed = False
    for paper in manifest["papers"]:
        row = extract(
            paper,
            root,
            manifest_dir,
            manifest["cited_work"],
            method,
            pattern,
            args.cache,
        )
        VALIDATOR.validate(row)
        sys.stdout.write(json.dumps(row, ensure_ascii=False) + "\n")
        sys.stdout.flush()
        failed |= row["outcome"] in {"source_unavailable", "extraction_failed"}
    return int(failed)
